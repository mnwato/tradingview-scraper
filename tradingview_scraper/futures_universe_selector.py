"""Futures trend-following universe selector and CLI helper.

This module builds on the existing tradingview-scraper Screener/Overview APIs
to construct a configurable selector for commodity futures. It supports config
loading (JSON/YAML), payload construction, pagination, post-filtering for
liquidity/volatility/trend rules, and optional export of results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import math
import os
import re
import sys
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from tradingview_scraper.settings import get_settings
from tradingview_scraper.symbols.overview import Overview
from tradingview_scraper.symbols.screener import Screener
from tradingview_scraper.symbols.utils import save_csv_file, save_json_file
from tradingview_scraper.utils.audit import AuditLedger

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

STABLE_BASES = {
    "USDT",
    "USDC",
    "USD",
    "BUSD",
    "FDUSD",
    "TUSD",
    "DAI",
    "PAX",
    "USDP",
    "EUR",
    "GBP",
    "AUD",
    "CAD",
    "NZD",
    "BIDR",
    "IDR",
    "TRY",
    "BRL",
    "MXN",
    "ZAR",
    "ARS",
    "COP",
    "UST",
    "USTC",
    "CHF",
    "JPY",
    "AEUR",
    "FUSD",
    "FUSDT",
    "USDS",
    "ZUSD",
    "USDM",
}


logger = logging.getLogger(__name__)

DEFAULT_COLUMNS = [
    "name",
    "description",
    "sector",
    "close",
    "volume",
    "change",
    "Recommend.All",
    "Recommend.MA",
    "Recommend.Other",
    "Value.Traded",
    "ADX",
    "Volatility.D",
    "Perf.W",
    "Perf.1M",
    "Perf.3M",
    "ATR",
]


DEFAULT_MOMENTUM = {"Perf.1M": 0.0, "Perf.3M": 0.0}

TABLE_DISPLAY_COLUMNS = [
    "symbol",
    "name",
    "close",
    "volume",
    "change",
    "Recommend.All",
    "ADX",
    "Volatility.D",
    "Perf.W",
    "Perf.1M",
    "Perf.3M",
]


class ExportConfig(BaseModel):
    enabled: bool = False
    type: str = "json"

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in {"json", "csv"}:
            raise ValueError("export.type must be 'json' or 'csv'")
        return value


class VolumeConfig(BaseModel):
    min: float = 0.0
    value_traded_min: float = 0.0
    per_exchange: dict[str, float] = Field(default_factory=dict)


class VolatilityConfig(BaseModel):
    min: float | None = None
    max: float | None = None
    atr_pct_max: float | None = None
    fallback_use_atr_pct: bool = True
    use_value_traded_floor: bool = False

    @model_validator(mode="after")
    def validate_bounds(self) -> "VolatilityConfig":
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("volatility.min cannot exceed volatility.max")
        return self


class RecentPerfConfig(BaseModel):
    enabled: bool = False
    required_fields: list[str] = Field(default_factory=list)
    abs_min: dict[str, float] = Field(default_factory=dict)
    abs_max: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_bounds(self) -> "RecentPerfConfig":
        for field, threshold in self.abs_min.items():
            if threshold < 0:
                raise ValueError(f"recent_perf.abs_min[{field}] must be non-negative")
        for field, threshold in self.abs_max.items():
            if threshold < 0:
                raise ValueError(f"recent_perf.abs_max[{field}] must be non-negative")
        for field, min_val in self.abs_min.items():
            max_val = self.abs_max.get(field)
            if max_val is not None and min_val > max_val:
                raise ValueError(f"recent_perf.abs_min[{field}] cannot exceed abs_max[{field}]")
        return self


class TrendRuleConfig(BaseModel):
    enabled: bool = True
    min: float | None = None
    horizons: dict[str, float] = Field(default_factory=dict)


class TrendConfig(BaseModel):
    logic: str = "AND"
    timeframe: str = "monthly"
    direction: str = "long"
    recommendation: TrendRuleConfig = Field(default_factory=lambda: TrendRuleConfig(min=0.3))
    adx: TrendRuleConfig = Field(default_factory=lambda: TrendRuleConfig(min=20))
    momentum: TrendRuleConfig = Field(default_factory=lambda: TrendRuleConfig(horizons=DEFAULT_MOMENTUM))
    confirmation_momentum: TrendRuleConfig = Field(default_factory=lambda: TrendRuleConfig(enabled=False, horizons={}))

    @field_validator("logic")
    @classmethod
    def validate_logic(cls, value: str) -> str:
        value_upper = value.upper()
        if value_upper not in {"AND", "OR"}:
            raise ValueError("trend.logic must be AND or OR")
        return value_upper

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        value_lower = value.lower()
        if value_lower not in {"daily", "weekly", "monthly"}:
            raise ValueError("trend.timeframe must be daily, weekly, or monthly")
        return value_lower

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        value_lower = value.lower()
        if value_lower not in {"long", "short"}:
            raise ValueError("trend.direction must be long or short")
        return value_lower


class ScreenConfig(BaseModel):
    timeframe: str
    logic: str = "AND"
    direction: str = "long"
    recommendation: TrendRuleConfig = Field(default_factory=TrendRuleConfig)
    adx: TrendRuleConfig = Field(default_factory=TrendRuleConfig)
    momentum: TrendRuleConfig = Field(default_factory=TrendRuleConfig)
    osc: TrendRuleConfig = Field(default_factory=TrendRuleConfig)
    volatility: TrendRuleConfig = Field(default_factory=TrendRuleConfig)

    @field_validator("logic")
    @classmethod
    def validate_logic(cls, value: str) -> str:
        value_upper = value.upper()
        if value_upper not in {"AND", "OR"}:
            raise ValueError("screen.logic must be AND or OR")
        return value_upper

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        value_lower = value.lower()
        if value_lower not in {"daily", "weekly", "monthly"}:
            raise ValueError("screen.timeframe must be daily, weekly, or monthly")
        return value_lower

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        value_lower = value.lower()
        if value_lower not in {"long", "short"}:
            raise ValueError("screen.direction must be long or short")
        return value_lower


class ExportMetadata(BaseModel):
    symbol: str = "futures_universe"
    data_category: str = "universe_selector"
    # Allow dynamic injection of extra metadata (e.g. logic, strategy_id)
    model_config = {"extra": "allow"}


class SelectorConfig(BaseModel):
    config_source: str | None = None
    markets: list[str] = Field(default_factory=lambda: ["futures"])
    exchanges: list[str] = Field(default_factory=list)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    include_symbols: list[str] = Field(default_factory=list)
    include_symbol_files: list[str] = Field(default_factory=list)
    exclude_symbols: list[str] = Field(default_factory=list)
    # Static universe support: allows configs to emit a deterministic basket even
    # when TradingView screener endpoints are unavailable or intentionally skipped.
    #
    # - If static_mode is true, the selector will emit static_symbols directly and
    #   will not query TradingView screeners.
    # - If static_mode is false but static_symbols is provided, the selector may
    #   fall back to static_symbols when the screener returns no rows.
    static_mode: bool = False
    static_symbols: list[str] = Field(default_factory=list)
    columns: list[str] = Field(
        default_factory=lambda: [
            "name",
            "description",
            "sector",
            "close",
            "volume",
            "change",
            "Recommend.All",
            "Recommend.MA",
            "Recommend.Other",
            "Value.Traded",
            "ADX",
            "Volatility.D",
            "Perf.W",
            "Perf.1M",
            "Perf.3M",
            "ATR",
        ]
    )
    volume: VolumeConfig = Field(default_factory=VolumeConfig)
    volatility: VolatilityConfig = Field(default_factory=VolatilityConfig)
    recent_perf: RecentPerfConfig = Field(default_factory=RecentPerfConfig)
    trend: TrendConfig = Field(default_factory=TrendConfig)
    trend_screen: ScreenConfig | None = None
    confirm_screen: ScreenConfig | None = None
    execute_screen: ScreenConfig | None = None  # optional; downstream execution can be handled separately
    sort_by: str = "volume"
    sort_order: str = "desc"
    final_sort_by: str | None = None
    final_sort_order: str = "desc"
    momentum_composite_fields: list[str] = Field(default_factory=list)
    momentum_composite_field_name: str = "momentum_zscore"
    limit: int = 50
    pagination_size: int = 1000
    retries: int = 3
    timeout: int = 30
    prefilter_limit: int | None = None
    dedupe_by_symbol: bool = True
    group_duplicates: bool = False
    attach_perp_counterparts: bool = False
    quote_priority: list[str] = Field(default_factory=lambda: ["USDT", "USDC", "FDUSD", "BUSD", "DAI", "USD"])
    include_stable_bases: bool = False
    ensure_symbols: list[str] = Field(default_factory=list)
    exclude_stable_bases: bool = False
    perp_exchange_priority: list[str] = Field(default_factory=list)
    market_cap_file: str | None = None
    market_cap_limit: int | None = None
    market_cap_rank_limit: int | None = None
    market_cap_floor: float | None = None
    market_cap_require_hit: bool = False
    base_universe_limit: int | None = None
    base_universe_sort_by: str = "Value.Traded"
    export: ExportConfig = Field(default_factory=ExportConfig)
    export_metadata: ExportMetadata = Field(default_factory=ExportMetadata)

    @field_validator("sort_order", "final_sort_order")
    @classmethod
    def validate_sort_order(cls, value: str) -> str:
        value_lower = value.lower()
        if value_lower not in {"asc", "desc"}:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return value_lower

    @field_validator("limit", "pagination_size", "retries", "timeout", "prefilter_limit")
    @classmethod
    def validate_positive(cls, value: int | None, info: Any) -> int | None:
        if value is None:
            return value
        if value <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return value

    @model_validator(mode="after")
    def validate_markets(self) -> "SelectorConfig":
        if not self.markets:
            raise ValueError("At least one market must be provided")
        return self


def _merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            # Concatenate lists
            merged_list = result[key] + value
            # Deduplicate simple lists (strings/ints) while preserving order
            # (Filters are dicts, so we don't deduplicate them here to be safe)
            if all(isinstance(x, (str, int, float)) for x in merged_list):
                result[key] = list(dict.fromkeys(merged_list))
            else:
                result[key] = merged_list
        else:
            result[key] = value
    return result


def _load_config_file(path: str) -> dict[str, Any]:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    ext = path_obj.suffix.lower()
    with path_obj.open("r", encoding="utf-8") as handle:
        if ext in {".yaml", ".yml"}:
            if yaml is None:
                raise ImportError("PyYAML is required to load YAML configs")
            raw = yaml.safe_load(handle) or {}
        else:
            raw = json.load(handle)

    # Handle base_preset inheritance
    if "base_preset" in raw:
        preset_path = raw.pop("base_preset")
        if not Path(preset_path).is_absolute():
            preset_path = path_obj.parent / preset_path
        base = _load_config_file(str(preset_path))
        raw = _merge(base, raw)

    return raw


def _load_symbol_file(path: Path) -> list[str]:
    if not path.exists():
        logger.warning("symbol list file not found: %s", path)
        return []

    try:
        content = path.read_text(encoding="utf-8").strip()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("failed reading symbol list %s: %s", path, exc)
        return []

    if not content:
        return []

    # Try JSON array first
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            symbols = [s for s in parsed if isinstance(s, str)]
        else:
            symbols = []
    except Exception:
        # Fallback: newline/comma-separated text
        parts = content.replace(",", "\n").splitlines()
        symbols = [p.strip() for p in parts if p.strip()]

    return [s.upper() for s in symbols]


def load_config(
    source: str | Mapping[str, Any] | None = None,
    overrides: Mapping[str, Any] | None = None,
    profile: str | None = None,
    scanner_type: str = "futures",
) -> SelectorConfig:
    """Load selector config from a file, mapping, or manifest profile with recursive inheritance."""
    raw: dict[str, Any] = {}
    base_dir: Path | None = None

    # 1. Load primary source (file or mapping)
    if isinstance(source, Mapping):
        raw = dict(source)
        base_dir = Path("configs")
    elif isinstance(source, str):
        raw = _load_config_file(source)
        base_dir = Path(source).parent

    # 2. Merge with manifest profile discovery config if provided
    if profile:
        from tradingview_scraper.settings import get_settings

        profile_discovery = get_settings().get_discovery_config(scanner_type)
        if profile_discovery:
            raw = _merge(raw, profile_discovery)
        if not base_dir:
            base_dir = Path("configs")

    if not raw and not profile and source is None:
        # Fallback to empty if nothing provided
        raw = {}

    # 3. Recursive Inheritance Resolution
    def resolve_inheritance(current_raw: dict[str, Any], current_base_dir: Path) -> dict[str, Any]:
        if "base_preset" in current_raw:
            preset_path_str = current_raw.pop("base_preset")
            preset_path = Path(preset_path_str)
            if not preset_path.is_absolute():
                preset_path = current_base_dir / preset_path

            base_raw = _load_config_file(str(preset_path))
            # Recurse first to resolve deeper layers
            resolved_base = resolve_inheritance(base_raw, preset_path.parent)
            # Merge current into resolved base
            return _merge(resolved_base, current_raw)
        return current_raw

    final_raw = resolve_inheritance(raw, base_dir or Path("configs"))

    if overrides:
        final_raw = _merge(final_raw, overrides)

    config = SelectorConfig.model_validate(final_raw)

    if isinstance(source, str):
        config.config_source = str(Path(source).resolve())

    if config.include_symbol_files:
        extra: list[str] = []
        for symfile in config.include_symbol_files:
            sym_path = Path(symfile)
            if not sym_path.is_absolute() and base_dir:
                sym_path = base_dir / sym_path
            extra.extend(_load_symbol_file(sym_path))
        if extra:
            merged = list(dict.fromkeys([s.upper() for s in (config.include_symbols + extra)]))
            config.include_symbols = merged

    return config


class FuturesUniverseSelector:
    """Selector orchestrating Screener + post-filters for futures."""

    REQUIRED_COLUMNS = [
        "name",
        "close",
        "volume",
        "change",
        "Recommend.All",
        "Recommend.MA",
        "Recommend.Other",
        "Volatility.D",
        "volume_change",
        "ROC",
        "type",
    ]

    def __init__(
        self,
        config: str | Mapping[str, Any] | SelectorConfig | None = None,
        screener: Screener | None = None,
        overview: Overview | None = None,
    ) -> None:
        self.config = config if isinstance(config, SelectorConfig) else load_config(config)

        # Auto-fix export symbol if default and market is different
        if self.config.export_metadata.symbol == "futures_universe" and self.config.markets:
            market_name = self.config.markets[0]
            if market_name != "futures":
                self.config.export_metadata.symbol = f"{market_name}_universe"

        self.screener = screener or Screener(export_result=False)
        self.overview = overview or Overview(export_result=False)
        self._market_cap_map: dict[str, float] | None = None

    def _build_columns(self) -> list[str]:
        columns: list[str] = []
        for col in self.REQUIRED_COLUMNS + self.config.columns:
            if col not in columns:
                columns.append(col)

        # Add timeframe-specific columns for screens
        for screen in [self.config.trend_screen, self.config.confirm_screen, self.config.execute_screen]:
            if screen:
                suffix = ""
                if screen.timeframe == "weekly":
                    suffix = "|1W"
                elif screen.timeframe == "monthly":
                    suffix = "|1M"

                if suffix:
                    if screen.adx.enabled and f"ADX{suffix}" not in columns:
                        columns.append(f"ADX{suffix}")
                    if screen.recommendation.enabled and f"Recommend.All{suffix}" not in columns:
                        columns.append(f"Recommend.All{suffix}")

        if self.config.volume.value_traded_min > 0 and "Value.Traded" not in columns:
            columns.append("Value.Traded")

        if self.config.market_cap_floor is not None and "market_cap_calc" not in columns:
            columns.append("market_cap_calc")

        if self.config.trend.timeframe in {"daily", "weekly"} and "Perf.W" not in columns:
            columns.append("Perf.W")
        return columns

    def _build_filters(self, market: str) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = []
        type_value = None
        if market == "futures":
            type_value = "futures"
        elif market == "forex":
            type_value = "forex"

        if type_value:
            filters.append({"left": "type", "operation": "equal", "right": type_value})

        if self.config.volume.min:
            filters.append(
                {
                    "left": "volume",
                    "operation": "greater",
                    "right": self.config.volume.min,
                }
            )

        if self.config.volume.value_traded_min > 0:
            filters.append(
                {
                    "left": "Value.Traded",
                    "operation": "greater",
                    "right": self.config.volume.value_traded_min,
                }
            )

        if self.config.filters:
            filters.extend(self.config.filters)

        return filters

    def _screen_market(
        self,
        market: str,
        filters: list[dict[str, Any]],
        columns: list[str],
        exchange: str | None = None,
        max_rows: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        collected: list[dict[str, Any]] = []
        errors: list[str] = []
        offset = 0
        page_size = self.config.pagination_size
        target = max_rows or self.config.limit

        while len(collected) < target:
            remaining = target - len(collected)
            batch_size = min(page_size, remaining)
            filters_with_exchange = list(filters)
            if exchange:
                filters_with_exchange = filters_with_exchange + [{"left": "exchange", "operation": "equal", "right": exchange}]
            response = self.screener.screen(
                market=market,
                filters=filters_with_exchange,
                columns=columns,
                sort_by=self.config.sort_by,
                sort_order=self.config.sort_order,
                limit=batch_size,
                range_start=offset,
            )

            if not response or response.get("status") != "success":
                errors.append(response.get("error", f"Failed to screen market {market}"))
                break

            data = response.get("data", [])
            if not data:
                break

            collected.extend(data)
            if len(data) < batch_size:
                break
            offset += batch_size

        return collected, errors

    @staticmethod
    def _extract_exchange(symbol: str) -> str | None:
        if not symbol or ":" not in symbol:
            return None
        return symbol.split(":", 1)[0]

    @staticmethod
    def _extract_base_quote(symbol: str) -> tuple[str, str]:
        if not symbol:
            return "", ""
        # Strip exchange prefix and perp suffix
        core = symbol.split(":", 1)[-1].upper().replace(".P", "").replace(".F", "")

        # Strip Dated Futures suffixes (e.g. Z2025, 27MAR2026)
        dated_patterns = [r"[0-9]{1,2}[A-Z]{1,3}[0-9]{2,4}$", r"[A-Z][0-9]{2,4}$"]
        for pat in dated_patterns:
            core = re.sub(pat, "", core)

        # Strip common numeric multipliers (e.g., 1000PEPE -> PEPE)
        core = re.sub(r"^[0-9]+", "", core)

        # Priority matches for institutional quotes to avoid greedy stablecoin matching (e.g. WIFUSDT)
        # We check these first because some broader stables (like FUSDT) can overlap with legitimate bases
        # Use longer, common quotes explicitly to avoid matching the shorter "USD" fragment too early
        for stable in ["USDT", "USDC", "FUSDT", "FDUSD", "FUSD", "BUSD", "DAI"]:
            if core.endswith(stable) and len(core) > len(stable):
                return core[: -len(stable)], stable

        for stable in sorted(STABLE_BASES, key=len, reverse=True):
            if core.endswith(stable) and len(core) > len(stable):
                return core[: -len(stable)], stable

        if len(core) == 6 and core.isalpha():
            return core[:3], core[3:]

        return core, ""

    @staticmethod
    def _forex_pair_identity(symbol: str) -> str:
        if not symbol:
            return ""

        core = symbol.split(":", 1)[-1].upper().replace(".P", "").replace(".F", "")
        if "." in core:
            core = core.split(".", 1)[0]
        core = re.sub(r"[^A-Z0-9]", "", core)

        base, quote = FuturesUniverseSelector._extract_base_quote(symbol)
        if base and quote:
            ident = re.sub(r"[^A-Z0-9]", "", (base + quote).upper())
            if len(ident) == 6 and ident.isalpha():
                return ident

        return core

    @staticmethod
    def _base_symbol(symbol: str) -> str:
        base, _ = FuturesUniverseSelector._extract_base_quote(symbol)
        return base

    @staticmethod
    def _is_perp(symbol: str) -> bool:
        return bool(symbol) and symbol.upper().endswith(".P")

    @staticmethod
    def _is_spot_symbol(symbol: str) -> bool:
        base, quote = FuturesUniverseSelector._extract_base_quote(symbol)
        return bool(base) and bool(quote)

    @staticmethod
    def _is_dated_symbol(symbol: str) -> bool:
        if not symbol:
            return False
        core = symbol.split(":", 1)[-1].upper().replace(".P", "")
        patterns = [r"[0-9]{1,2}[A-Z][0-9]{2,4}$", r"[A-Z]{1,3}[0-9]{2,4}$"]
        return any(re.search(pat, core) for pat in patterns)

    def _evaluate_liquidity(self, row: dict[str, Any]) -> bool:
        volume_value = row.get("volume")
        value_traded = row.get("Value.Traded")
        vt_floor = self.config.volume.value_traded_min or 0
        vol_floor = self.config.volume.min or 0

        # If Value.Traded is present, enforce that floor first
        if value_traded is not None and value_traded < vt_floor:
            return False

        if volume_value is None:
            return vol_floor <= 0
        symbol = row.get("symbol", "")
        exchange = self._extract_exchange(symbol)
        if exchange and exchange in self.config.volume.per_exchange:
            threshold = self.config.volume.per_exchange[exchange]
        else:
            threshold = self.config.volume.min
        return volume_value >= threshold

    def _evaluate_volatility(self, row: dict[str, Any]) -> tuple[bool, float | None]:
        vol_cfg = self.config.volatility
        volatility_value = row.get("Volatility.D")
        atr_pct: float | None = None

        if vol_cfg.fallback_use_atr_pct:
            atr = row.get("ATR")
            close = row.get("close")
            if atr is not None and close not in (None, 0):
                atr_pct = atr / close
                row["atr_pct"] = atr_pct

        checks_present = any(value is not None for value in (vol_cfg.min, vol_cfg.max, vol_cfg.atr_pct_max))
        if not checks_present:
            return True, atr_pct

        if volatility_value is not None:
            above_min = vol_cfg.min is None or volatility_value >= vol_cfg.min
            below_max = vol_cfg.max is None or volatility_value <= vol_cfg.max
            if above_min and below_max:
                return True, atr_pct

        if atr_pct is not None and vol_cfg.atr_pct_max is not None:
            if atr_pct <= vol_cfg.atr_pct_max:
                return True, atr_pct

        return False, atr_pct

    def _apply_recent_perf_filter(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cfg = self.config.recent_perf
        if not cfg.enabled:
            return rows

        required_fields = [f for f in (cfg.required_fields or []) if f]
        abs_min = cfg.abs_min or {}
        abs_max = cfg.abs_max or {}

        def _coerce(value: Any) -> float | None:
            try:
                num = float(value)
            except (TypeError, ValueError):
                return None
            if math.isnan(num):
                return None
            return num

        filtered: list[dict[str, Any]] = []
        for row in rows:
            ok = True

            for field in required_fields:
                if _coerce(row.get(field)) is None:
                    ok = False
                    break
            if not ok:
                continue

            for field, threshold in abs_min.items():
                num = _coerce(row.get(field))
                if num is None or abs(num) < threshold:
                    ok = False
                    break
            if not ok:
                continue

            for field, threshold in abs_max.items():
                num = _coerce(row.get(field))
                if num is None or abs(num) > threshold:
                    ok = False
                    break

            if ok:
                filtered.append(row)

        return filtered

    def _evaluate_trend(self, row: dict[str, Any]) -> dict[str, bool]:
        trend_cfg = self.config.trend
        checks: dict[str, bool] = {}
        is_long = trend_cfg.direction == "long"

        if trend_cfg.recommendation.enabled:
            rec_min = trend_cfg.recommendation.min
            rec_value = row.get("Recommend.All")
            rec_pass = False
            if rec_min is not None and rec_value is not None:
                rec_pass = rec_value >= rec_min if is_long else rec_value <= rec_min
            checks["recommendation"] = rec_pass
            # Debug Trace for high-rating assets
            if abs(float(rec_value or 0)) > 0.5:
                logger.debug(f"TRACE: Symbol={row.get('symbol')} Rec={rec_value} Min={rec_min} Pass={rec_pass}")

        if trend_cfg.adx.enabled:
            adx_min = trend_cfg.adx.min
            adx_value = row.get("ADX")
            checks["adx"] = adx_min is not None and adx_value is not None and adx_value >= adx_min

        if trend_cfg.momentum.enabled:
            horizons = trend_cfg.momentum.horizons or {}
            if horizons == DEFAULT_MOMENTUM:
                if trend_cfg.timeframe == "daily":
                    horizons = {"change": 0.0, "Perf.W": 0.0}
                elif trend_cfg.timeframe == "weekly":
                    horizons = {"Perf.W": 0.0}
            if not horizons:
                if trend_cfg.timeframe == "daily":
                    horizons = {"change": 0.0, "Perf.W": 0.0}
                elif trend_cfg.timeframe == "weekly":
                    horizons = {"Perf.W": 0.0}
                else:
                    horizons = DEFAULT_MOMENTUM

            momentum_pass = True
            for field, threshold in horizons.items():
                value = row.get(field)
                if value is None:
                    momentum_pass = False
                    break
                if is_long:
                    if value <= threshold:
                        momentum_pass = False
                        break
                else:
                    if value >= threshold:
                        momentum_pass = False
                        break
            checks["momentum"] = momentum_pass

        if trend_cfg.confirmation_momentum.enabled:
            conf_pass = True
            for field, threshold in (trend_cfg.confirmation_momentum.horizons or {}).items():
                value = row.get(field)
                if value is None:
                    conf_pass = False
                    break
                if is_long:
                    if value <= threshold:
                        conf_pass = False
                        break
                else:
                    if value >= threshold:
                        conf_pass = False
                        break
            checks["confirmation_momentum"] = conf_pass

        enabled_checks = {k: v for k, v in checks.items() if v is not None}
        if not enabled_checks:
            combined = True
        elif trend_cfg.logic == "AND":
            combined = all(enabled_checks.values())
        else:
            combined = any(enabled_checks.values())

        checks["combined"] = combined
        return checks

    def _evaluate_screen(self, row: dict[str, Any], screen: ScreenConfig) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        is_long = screen.direction == "long"

        suffix = ""
        if screen.timeframe == "weekly":
            suffix = "|1W"
        elif screen.timeframe == "monthly":
            suffix = "|1M"

        if screen.recommendation.enabled:
            rec_min = screen.recommendation.min
            rec_value = row.get(f"Recommend.All{suffix}") or row.get("Recommend.All")
            if rec_min is None:
                rec_pass = True
            else:
                rec_pass = False
                if rec_value is not None:
                    rec_pass = rec_value >= rec_min if is_long else rec_value <= rec_min
            checks["recommendation"] = rec_pass

        if screen.adx.enabled:
            adx_min = screen.adx.min
            adx_value = row.get(f"ADX{suffix}") or row.get("ADX")
            if adx_min is None:
                checks["adx"] = True
            else:
                checks["adx"] = adx_value is not None and adx_value >= adx_min

        if screen.momentum.enabled:
            horizons = screen.momentum.horizons or {}
            if not horizons:
                checks["momentum"] = True
            else:
                momentum_pass = True
                for field, threshold in horizons.items():
                    value = row.get(field)
                    if value is None:
                        momentum_pass = False
                        break
                    if is_long:
                        if value <= threshold:
                            momentum_pass = False
                            break
                    else:
                        if value >= threshold:
                            momentum_pass = False
                            break
                checks["momentum"] = momentum_pass

        if screen.osc.enabled:
            horizons = screen.osc.horizons or {}
            if not horizons:
                checks["osc"] = True
            else:
                osc_pass = True
                for field, threshold in horizons.items():
                    value = row.get(field)
                    if value is None:
                        osc_pass = False
                        break
                    if is_long:
                        if value >= threshold:
                            osc_pass = False
                            break
                    else:
                        if value <= threshold:
                            osc_pass = False
                            break
                checks["osc"] = osc_pass

        if screen.volatility.enabled:
            horizons = screen.volatility.horizons or {}
            if not horizons:
                checks["volatility"] = True
            else:
                vol_pass = True
                for field, threshold in horizons.items():
                    value = row.get(field)
                    if value is None:
                        vol_pass = False
                        break
                    if is_long:
                        if value >= threshold:
                            vol_pass = False
                            break
                    else:
                        if value <= threshold:
                            vol_pass = False
                            break
                checks["volatility"] = vol_pass

        enabled_checks = {k: v for k, v in checks.items() if v is not None}
        if not enabled_checks:
            combined = True
        elif screen.logic == "AND":
            combined = all(enabled_checks.values())
        else:
            combined = any(enabled_checks.values())

        checks["combined"] = combined
        return checks

    def _apply_basic_filters(self, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        include_set = set(s.upper() for s in self.config.include_symbols)
        exclude_set = set(s.upper() for s in self.config.exclude_symbols)
        exchange_set = set(self.config.exchanges)

        filtered: list[dict[str, Any]] = []
        for row in rows:
            symbol = row.get("symbol", "").upper()

            exchange = self._extract_exchange(symbol)
            base_symbol = self._base_symbol(symbol)

            if self.config.exclude_stable_bases and base_symbol in STABLE_BASES:
                continue

            if include_set:
                base_match = base_symbol in include_set
                if symbol not in include_set and not base_match:
                    continue
            if symbol in exclude_set or base_symbol in exclude_set:
                continue
            if exchange_set and exchange not in exchange_set:
                continue

            filtered.append(row)
        return filtered

    def _apply_strategy_filters(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for row in rows:
            passes = row.get("passes", {}) if "passes" in row else {}
            trend_checks = self._evaluate_trend(row)
            passes.update({f"trend_{k}": v for k, v in trend_checks.items()})

            screens_combined = True
            if trend_checks.get("combined", True):
                if self.config.trend_screen:
                    screen_checks = self._evaluate_screen(row, self.config.trend_screen)
                    passes.update({f"trend_screen_{k}": v for k, v in screen_checks.items()})
                    screens_combined = screens_combined and screen_checks.get("combined", True)
                if screens_combined and self.config.confirm_screen:
                    confirm_checks = self._evaluate_screen(row, self.config.confirm_screen)
                    passes.update({f"confirm_screen_{k}": v for k, v in confirm_checks.items()})
                    screens_combined = screens_combined and confirm_checks.get("combined", True)
                if screens_combined and self.config.execute_screen:
                    execute_checks = self._evaluate_screen(row, self.config.execute_screen)
                    passes.update({f"execute_screen_{k}": v for k, v in execute_checks.items()})
                    screens_combined = screens_combined and execute_checks.get("combined", True)

            passes["all"] = trend_checks.get("combined", True) and screens_combined
            row["passes"] = passes
            if passes["all"]:
                filtered.append(row)
        return filtered

    def _apply_momentum_composite(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        fields = [f for f in self.config.momentum_composite_fields if f]
        if not fields:
            return rows

        stats = {}
        for field in fields:
            values = [float(r[field]) for r in rows if isinstance(r.get(field), (int, float))]
            if not values:
                continue
            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / len(values)
            std_val = variance**0.5
            if std_val > 0:
                stats[field] = (mean_val, std_val)

        composite_field = self.config.momentum_composite_field_name or "momentum_zscore"
        if not stats:
            for row in rows:
                row[composite_field] = None
            return rows

        for row in rows:
            scores = []
            for field, (mean_val, std_val) in stats.items():
                val = row.get(field)
                if isinstance(val, (int, float)):
                    scores.append((val - mean_val) / std_val)
            row[composite_field] = sum(scores) / len(scores) if scores else None

        return rows

    def _load_market_cap_map(self) -> dict[str, float]:
        if self._market_cap_map is not None:
            return self._market_cap_map
        path = self.config.market_cap_file
        if not path:
            self._market_cap_map = {}
            return self._market_cap_map
        path_obj = Path(path)
        if not path_obj.exists():
            logging.warning("Market cap file not found: %s", path)
            self._market_cap_map = {}
            return self._market_cap_map
        caps: dict[str, float] = {}
        try:
            if path_obj.suffix.lower() == ".json":
                with path_obj.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    for key, val in payload.items():
                        try:
                            caps[str(key).upper()] = float(val)
                        except (TypeError, ValueError):
                            continue
                elif isinstance(payload, list):
                    for item in payload:
                        if not isinstance(item, Mapping):
                            continue
                        sym = item.get("symbol") or item.get("base")
                        cap_val = item.get("market_cap") or item.get("cap")
                        if sym and isinstance(cap_val, (int, float)):
                            core = str(sym).upper().replace(".P", "")
                            if ":" in core:
                                core = core.split(":", 1)[-1]
                            # strip any stable quote suffix from the market cap key
                            for stable in sorted(STABLE_BASES, key=len, reverse=True):
                                if core.endswith(stable) and len(core) > len(stable):
                                    core = core[: -len(stable)]
                                    break
                            caps[core] = float(cap_val)
            elif path_obj.suffix.lower() in {".csv", ".tsv"}:
                with path_obj.open("r", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    for row in reader:
                        sym = row.get("symbol") or row.get("base")
                        cap_val = row.get("market_cap") or row.get("cap")
                        if sym and cap_val is not None:
                            try:
                                core = str(sym).upper().replace(".P", "")
                                if ":" in core:
                                    core = core.split(":", 1)[-1]
                                for stable in sorted(STABLE_BASES, key=len, reverse=True):
                                    if core.endswith(stable) and len(core) > len(stable):
                                        core = core[: -len(stable)]
                                        break
                                caps[core] = float(cap_val)
                            except (TypeError, ValueError):
                                continue
        except Exception as exc:  # pragma: no cover - defensive
            logging.warning("Failed to load market cap file %s: %s", path, exc)
            caps = {}
        self._market_cap_map = caps
        return self._market_cap_map

    def _apply_market_cap_filter(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        initial_count = len(rows)
        cap_map = self._load_market_cap_map()

        # Annotate with external market cap for visibility/debugging and for floor guard
        for row in rows:
            base = self._base_symbol(row.get("symbol", ""))
            cap_val = cap_map.get(base)
            if cap_val is not None:
                row["market_cap_external"] = cap_val

        # Guard B: Floor-based (Screener OR External)
        if self.config.market_cap_floor is not None:
            rows = [r for r in rows if max(r.get("market_cap_calc") or 0, r.get("market_cap_external") or 0) >= self.config.market_cap_floor]
            logger.info("Floor guard (%s) reduced rows from %d to %d", self.config.market_cap_floor, initial_count, len(rows))

        # Guard A: Rank-based (from external file)
        if cap_map and self.config.market_cap_rank_limit:
            # select top bases by cap to establish the "Allowed Rank" set
            tops = sorted(((b, v) for b, v in cap_map.items()), key=lambda x: x[1], reverse=True)[: self.config.market_cap_rank_limit]
            allowed_bases = {b for b, _ in tops}
            before_rank = len(rows)
            rows = [r for r in rows if self._base_symbol(r.get("symbol", "")) in allowed_bases]
            logger.info("Rank guard (%d) reduced rows from %d to %d", self.config.market_cap_rank_limit, before_rank, len(rows))

        # market_cap_limit is the old field, keep it for backward compatibility
        if cap_map and self.config.market_cap_limit and not self.config.market_cap_rank_limit:
            tops = sorted(((b, v) for b, v in cap_map.items()), key=lambda x: x[1], reverse=True)[: self.config.market_cap_limit]
            allowed_bases = {b for b, _ in tops}
            rows = [r for r in rows if self._base_symbol(r.get("symbol", "")) in allowed_bases]

        return rows

    def _aggregate_by_base(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sort_field = self.config.final_sort_by or self.config.sort_by or "Value.Traded"
        descending = (self.config.final_sort_order or "desc").lower() == "desc"
        best_by_base: dict[str, dict[str, Any]] = {}
        all_members: dict[str, list[str]] = {}
        agg_vt: dict[str, float] = {}
        agg_vol: dict[str, float] = {}
        priority = [p.upper() for p in self.config.perp_exchange_priority]

        # Use config.quote_priority if available
        quote_prio_list = self.config.quote_priority or ["USDT", "USDC", "FDUSD", "BUSD", "DAI", "USD"]
        quote_priority_map = {q.upper(): idx for idx, q in enumerate(quote_prio_list)}

        markets_lower = [m.lower() for m in (self.config.markets or [])]
        is_forex = "forex" in markets_lower

        def group_key(symbol: str) -> str:
            if is_forex:
                return self._forex_pair_identity(symbol)
            return self._base_symbol(symbol)

        def exchange_rank(symbol: str) -> int:
            exchange = self._extract_exchange(symbol) or ""
            if exchange.upper() in priority:
                return priority.index(exchange.upper())
            return len(priority)

        for row in rows:
            symbol = row.get("symbol", "")
            base = group_key(symbol)

            # Stable-to-Stable exclusion: If base is also in STABLE_BASES, exclude unless it's a stablecoin scan
            if base in STABLE_BASES and not self.config.include_stable_bases:
                continue

            # Track total base metrics across all quotes/instruments
            agg_vt[base] = agg_vt.get(base, 0.0) + float(row.get("Value.Traded") or 0.0)
            agg_vol[base] = agg_vol.get(base, 0.0) + float(row.get("volume") or 0.0)

            if base not in all_members:
                all_members[base] = []
            if symbol not in all_members[base]:
                all_members[base].append(symbol)

            current = best_by_base.get(base)
            if current is None:
                best_by_base[base] = row
                continue

            candidate_value = row.get(sort_field) or 0
            best_value = current.get(sort_field) or 0

            # 1. Quote Priority (e.g. USDT > USDC)
            _, cand_quote = self._extract_base_quote(symbol)
            _, current_quote = self._extract_base_quote(current.get("symbol", ""))

            cand_q_rank = quote_priority_map.get(cand_quote, 999)
            curr_q_rank = quote_priority_map.get(current_quote, 999)

            better = False
            if isinstance(candidate_value, (int, float)) and isinstance(best_value, (int, float)):
                if cand_q_rank < curr_q_rank:
                    # Prefer candidate if its liquidity is at least 30% of best
                    if candidate_value > best_value * 0.3:
                        better = True
                elif cand_q_rank > curr_q_rank:
                    # Prefer current if its liquidity is at least 30% of candidate
                    if best_value > candidate_value * 0.3:
                        better = False
            else:
                # Non-numeric sort field (e.g. name): stick strictly to quote priority
                if cand_q_rank < curr_q_rank:
                    better = True
                elif cand_q_rank > curr_q_rank:
                    better = False

            if better:
                best_by_base[base] = row
                continue

            # If quotes are same rank, continue with other preferences
            if cand_q_rank != curr_q_rank:
                # One is definitely preferred by quote rank and we already decided
                continue

            # 2. Prefer Linear Perps over Inverse Perps (if both are perps) handled by quote priority mostly

            # 3. Exchange Rank preference
            if exchange_rank(symbol) < exchange_rank(current.get("symbol", "")):
                # Only switch if liquidity is comparable
                if candidate_value > best_value * 0.5:
                    best_by_base[base] = row
                    continue

            # 5. Tie-break by Value.Traded
            try:
                if descending:
                    if candidate_value > best_value:
                        best_by_base[base] = row
                else:
                    if candidate_value < best_value:
                        best_by_base[base] = row
            except TypeError:
                continue

        results = list(best_by_base.values())
        for row in results:
            base = group_key(row.get("symbol", ""))

            # Preserve representative (single-venue) metrics
            row["Value.Traded_rep"] = row.get("Value.Traded")
            row["volume_rep"] = row.get("volume")

            # Override with aggregated metrics across all members in this identity
            row["Value.Traded"] = agg_vt.get(base, row.get("Value.Traded"))
            row["volume"] = agg_vol.get(base, row.get("volume"))

            if self.config.group_duplicates:
                row["alternates"] = [s for s in all_members.get(base, []) if s != row.get("symbol")]

        return results

    def _dedupe_by_base(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return one representative row per base symbol."""
        return self._aggregate_by_base(rows)

    def _sort_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Use final_sort_by if set, otherwise fallback to sort_by
        sort_field = self.config.final_sort_by or self.config.sort_by
        if not sort_field:
            return rows

        # Use final_sort_order if set, otherwise fallback to sort_order
        order = self.config.final_sort_order if self.config.final_sort_by else self.config.sort_order
        reverse = (order or "desc").lower() == "desc"

        def sort_key(row: dict[str, Any]):
            val = row.get(sort_field)
            if isinstance(val, (int, float)):
                return val
            # Handle non-numeric sorts (like name) safely
            if isinstance(val, str):
                return val
            # Fallback for None or other types: push to end
            return float("-inf") if reverse else float("inf")

        return sorted(rows, key=sort_key, reverse=reverse)

    def _select_perp_candidate(self, base: str, perps: list[dict[str, Any]]) -> dict[str, Any] | None:
        candidates = [p for p in perps if self._base_symbol(p.get("symbol", "")) == base]
        if not candidates:
            return None

        priority = [p.upper() for p in self.config.perp_exchange_priority]
        field = self.config.final_sort_by or self.config.sort_by or "volume"
        reverse = (self.config.final_sort_order or "desc") == "desc"

        def exchange_rank(symbol: str) -> int:
            exchange = self._extract_exchange(symbol) or ""
            if exchange.upper() in priority:
                return priority.index(exchange.upper())
            return len(priority)

        def candidate_key(row: dict[str, Any]):
            exchange_score = exchange_rank(row.get("symbol", ""))
            val = row.get(field)
            if isinstance(val, (int, float)):
                metric = -val if reverse else val
            else:
                metric = float("inf")
            return (exchange_score, metric)

        return sorted(candidates, key=candidate_key)[0]

    def _attach_perp_counterparts(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        spot_rows: list[dict[str, Any]] = [r for r in rows if not self._is_perp(r.get("symbol", ""))]
        perp_rows = [r for r in rows if self._is_perp(r.get("symbol", ""))]

        spot_unique = self._dedupe_by_base(spot_rows)
        spot_sorted = self._sort_rows(spot_unique)
        base_trimmed = spot_sorted[: self.config.limit]

        ensure_set = {s.upper() for s in self.config.ensure_symbols}
        if ensure_set:
            spot_lookup = {(r.get("symbol", "") or "").upper(): r for r in spot_sorted}
            existing = {row.get("symbol") for row in base_trimmed}
            for symbol in ensure_set:
                row = spot_lookup.get(symbol)
                if row and row.get("symbol") not in existing:
                    base_trimmed.append(row)
                    existing.add(row.get("symbol"))

        seen_symbols = {row.get("symbol") for row in base_trimmed}
        extras: list[dict[str, Any]] = []
        for row in base_trimmed:
            base = self._base_symbol(row.get("symbol", ""))
            perp_candidate = self._select_perp_candidate(base, perp_rows)
            if perp_candidate and perp_candidate.get("symbol") not in seen_symbols:
                extras.append(perp_candidate)
                seen_symbols.add(perp_candidate.get("symbol"))

        return base_trimmed + extras

    def _export_results(self, data: list[dict[str, Any]]) -> None:
        if not self.config.export.enabled:
            return

        if self.config.export.type == "json":
            run_id = os.getenv("TV_EXPORT_RUN_ID") or None
            markets = list(self.config.markets or [])
            markets_lower = [m.lower() for m in markets]
            direction = (self.config.trend.direction or "").upper()
            primary_exchange = self.config.exchanges[0] if len(self.config.exchanges or []) == 1 else None

            product = None
            if "crypto" in markets_lower:
                all_perps = all(self._is_perp(r.get("symbol", "")) for r in data) if data else False
                product = "PERP" if all_perps else "CRYPTO"
            elif "futures" in markets_lower:
                product = "FUTURES"
            elif "forex" in markets_lower:
                product = "FOREX"
            elif "america" in markets_lower:
                product = "STOCKS"

            payload = {
                "meta": {
                    "schema": "universe_selector_export",
                    "schema_version": 1,
                    "run_id": run_id,
                    "generated_at": datetime.now().isoformat(timespec="seconds"),
                    "selector": self.__class__.__name__,
                    "config_source": self.config.config_source,
                    # Merge all export metadata fields (including injected logic)
                    **self.config.export_metadata.model_dump(),
                    "export_symbol": self.config.export_metadata.symbol,  # Explicit override ensuring key presence
                    "data_category": self.config.export_metadata.data_category,
                    "direction": direction,
                    "product": product,
                    "primary_exchange": primary_exchange,
                    "markets": markets,
                    "exchanges": list(self.config.exchanges or []),
                    "trend": self.config.trend.model_dump(),
                },
                "data": data,
            }
            save_json_file(
                data=payload,
                symbol=self.config.export_metadata.symbol,
                data_category=self.config.export_metadata.data_category,
                run_id=run_id,
            )
        else:
            save_csv_file(
                data=data,
                symbol=self.config.export_metadata.symbol,
                data_category=self.config.export_metadata.data_category,
            )

    def process_data(self, raw_data: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Processes raw screened data through the selector's post-filtering and aggregation pipeline.
        """
        logger.info(f"AUDIT: Starting process_data with {len(raw_data)} candidates.")

        # Global Ensure: Track symbols that MUST be in the result if they exist in raw data
        ensure_set = {s.upper() for s in self.config.ensure_symbols}
        ensured_rows = [r for r in raw_data if r.get("symbol", "").upper() in ensure_set]

        # 1. Basic Filters (Symbol, type, stable exclusion)
        rows_step1 = self._apply_basic_filters(raw_data)
        logger.info(f"AUDIT: Step 1 (Basic Filters) dropped {len(raw_data) - len(rows_step1)} items.")

        # 2. Market Cap Guard (Rank and Floor)
        rows_step2 = self._apply_market_cap_filter(rows_step1)
        logger.info(f"AUDIT: Step 2 (Market Cap) dropped {len(rows_step1) - len(rows_step2)} items.")

        # 3. Volatility Filter
        rows_step3 = []
        for r in rows_step2:
            passed, val = self._evaluate_volatility(r)
            if passed:
                rows_step3.append(r)
            else:
                logger.info(f"AUDIT: Dropped {r.get('symbol')} due to Volatility (Value={val})")
        logger.info(f"AUDIT: Step 3 (Volatility) dropped {len(rows_step2) - len(rows_step3)} items.")

        # 4. Liquidity Filter (Floor)
        rows_step4 = []
        for r in rows_step3:
            if self._evaluate_liquidity(r):
                rows_step4.append(r)
            else:
                logger.info(f"AUDIT: Dropped {r.get('symbol')} due to Liquidity (Vol={r.get('volume')}, Val={r.get('Value.Traded')})")
        logger.info(f"AUDIT: Step 4 (Liquidity) dropped {len(rows_step3) - len(rows_step4)} items.")

        # 5. Recent performance / data completeness guard
        rows_step5 = self._apply_recent_perf_filter(rows_step4)
        logger.info(f"AUDIT: Step 5 (Recent Perf) dropped {len(rows_step4) - len(rows_step5)} items.")

        # Add back ensured rows if they were filtered out
        # (This logic implies ensured rows might have failed above checks but are forced back in?
        #  If so, we should log that too).
        seen_symbols = {r.get("symbol") for r in rows_step5}
        forced_back = 0
        for er in ensured_rows:
            if er.get("symbol") not in seen_symbols:
                rows_step5.append(er)
                forced_back += 1
        if forced_back > 0:
            logger.info(f"AUDIT: Forced back {forced_back} ensured symbols.")

        rows = rows_step5

        # 6. Aggregation (Deduplicate by base currency)
        if self.config.dedupe_by_symbol and not self.config.attach_perp_counterparts:
            before_dedupe = len(rows)
            rows = self._aggregate_by_base(rows)
            logger.info(f"AUDIT: Step 6 (Deduplication) reduced count from {before_dedupe} to {len(rows)} (merged {before_dedupe - len(rows)}).")

        # 7. Sorting & Limiting (Base Universe)
        base_sort_field = self.config.base_universe_sort_by or "Value.Traded"
        rows.sort(key=lambda x: x.get(base_sort_field) or 0, reverse=True)

        if self.config.base_universe_limit:
            before_limit = len(rows)
            rows = rows[: self.config.base_universe_limit]
            if len(rows) < before_limit:
                logger.info(f"AUDIT: Step 7 (Base Limit) dropped {before_limit - len(rows)} items.")

        # 8. Strategy Filters (Trend, Screens)
        filtered = self._apply_strategy_filters(rows)
        logger.info(f"AUDIT: Step 8 (Strategy Filters) dropped {len(rows) - len(filtered)} items.")

        # Log specific strategy drops if count > 0
        if len(rows) > len(filtered):
            survivors = {r.get("symbol") for r in filtered}
            for r in rows:
                if r.get("symbol") not in survivors:
                    logger.info(f"AUDIT: Dropped {r.get('symbol')} due to Strategy Filters (Passes: {r.get('passes')})")

        if self.config.momentum_composite_fields:
            filtered = self._apply_momentum_composite(filtered)

        if self.config.attach_perp_counterparts:
            trimmed = self._attach_perp_counterparts(filtered)
        else:
            final_sorted = self._sort_rows(filtered)
            trimmed = final_sorted[: self.config.limit]
            if len(trimmed) < len(final_sorted):
                logger.info(f"AUDIT: Step 9 (Final Limit) dropped {len(final_sorted) - len(trimmed)} items.")

        # Final Uniqueness Guard: Ensure no duplicate symbols in final output
        seen_final: set[str] = set()
        unique_final: list[dict[str, Any]] = []
        for r in trimmed:
            sym = r.get("symbol")
            if sym and sym not in seen_final:
                unique_final.append(r)
                seen_final.add(sym)
        trimmed = unique_final

        if self.config.export.enabled:
            self._export_results(trimmed)

        return {
            "status": "success",
            "data": trimmed,
            "total_candidates": len(raw_data),
            "total_selected": len(trimmed),
        }

    def build_payloads(self, columns: list[str] | None = None) -> list[dict[str, Any]]:
        """Build screener payloads for dry-run and execution.

        This must match the actual `run()` execution path (including exchange loops)
        to keep dry-run output faithful.
        """
        resolved_columns = columns or self._build_columns()
        payloads: list[dict[str, Any]] = []

        for market in self.config.markets:
            filters = self._build_filters(market)
            prefilter_limit = self.config.prefilter_limit or self.config.limit

            if self.config.exchanges:
                for exchange in self.config.exchanges:
                    payloads.append(
                        {
                            "market": market,
                            "filters": list(filters),
                            "columns": resolved_columns,
                            "sort_by": self.config.sort_by,
                            "sort_order": self.config.sort_order,
                            "limit": prefilter_limit,
                            "pagination_size": self.config.pagination_size,
                            "exchange": exchange,
                        }
                    )
            else:
                payloads.append(
                    {
                        "market": market,
                        "filters": list(filters),
                        "columns": resolved_columns,
                        "sort_by": self.config.sort_by,
                        "sort_order": self.config.sort_order,
                        "limit": prefilter_limit,
                        "pagination_size": self.config.pagination_size,
                        "exchange": None,
                    }
                )

        return payloads

    def run(self, dry_run: bool = False) -> dict[str, Any]:
        """Execute the selector pipeline."""
        settings = get_settings()
        run_dir = settings.prepare_summaries_run_dir()
        ledger = AuditLedger(run_dir) if settings.features.feat_audit_ledger else None

        columns = self._build_columns()
        payloads = self.build_payloads(columns=columns)

        if dry_run:
            return {
                "status": "dry_run",
                "payloads": payloads,
                "config": self.config.model_dump(),
            }

        if ledger:
            # Record scanner intent
            config_json = json.dumps(self.config.model_dump(), sort_keys=True)
            config_hash = hashlib.sha256(config_json.encode()).hexdigest()
            ledger.record_intent(
                step="discovery_scan",
                params={"scanner_type": self.config.export_metadata.symbol, "limit": self.config.limit},
                input_hashes={"scanner_config": config_hash},
            )

        aggregated: list[dict[str, Any]] = []
        errors: list[str] = []

        if self.config.static_mode:
            static_list = [str(s) for s in (self.config.static_symbols or []) if str(s).strip()]
            if static_list:
                # To maintain metadata consistency, we use the overview API to fetch fields
                # for the static symbols.
                logger.info("Static mode enabled. Fetching metadata for %d symbols...", len(static_list))
                try:
                    # We might need to split symbols by market if they are mixed
                    # For now, assume they are mostly in the primary market or try 'america' as catch-all
                    market = self.config.markets[0] if self.config.markets else "america"
                    response = self.screener.screen(
                        market=market, filters=[{"left": "name", "operation": "in_range", "right": [s.split(":")[-1] for s in static_list]}], columns=columns, limit=len(static_list)
                    )
                    if response and response.get("status") == "success":
                        aggregated = response.get("data", [])
                        # Cross-check symbols to ensure we got the right ones
                        found_symbols = {r.get("symbol") for r in aggregated}
                        for s in static_list:
                            if s not in found_symbols:
                                aggregated.append({"symbol": s})
                    else:
                        aggregated = [{"symbol": s} for s in static_list]
                except Exception as e:
                    logger.warning("Failed to fetch metadata for static symbols: %s", e)
                    aggregated = [{"symbol": s} for s in static_list]
            else:
                aggregated = []
        else:
            for payload in payloads:
                market_rows, market_errors = self._screen_market(
                    payload["market"],
                    payload["filters"],
                    payload["columns"],
                    exchange=payload.get("exchange"),
                    max_rows=payload.get("limit"),
                )
                aggregated.extend(market_rows)
                errors.extend(market_errors)

            if not aggregated and self.config.static_symbols:
                aggregated = [{"symbol": str(s)} for s in self.config.static_symbols if str(s).strip()]

        result = self.process_data(aggregated)

        if ledger:
            # Record scanner outcome
            data_json = json.dumps(result.get("data", []), sort_keys=True)
            data_hash = hashlib.sha256(data_json.encode()).hexdigest()
            ledger.record_outcome(
                step="discovery_scan",
                status="success" if not errors else "partial_success",
                output_hashes={"scanned_symbols": data_hash},
                metrics={"total_selected": result.get("total_selected", 0), "errors": len(errors)},
            )

        if errors:
            result["status"] = "partial_success"
            result["errors"] = errors
        return result


def _format_markdown_table(rows: list[Mapping[str, Any]], columns: list[str] | None = None) -> str:
    if not rows:
        return "No data"

    configured_cols = columns or []
    ordered_cols: list[str] = []
    seen = set()

    for col in ["symbol"] + [c for c in configured_cols if c != "symbol"]:
        if col in seen:
            continue
        if any(col in row for row in rows):
            ordered_cols.append(col)
            seen.add(col)

    if not ordered_cols:
        for key in rows[0].keys():
            if key not in seen:
                ordered_cols.append(key)
                seen.add(key)

    header = "| " + " | ".join(ordered_cols) + " |"
    separator = "| " + " | ".join("---" for _ in ordered_cols) + " |"
    data_lines: list[str] = []

    for row in rows:
        cells = []
        for col in ordered_cols:
            value = row.get(col, "")
            if isinstance(value, float):
                cell = f"{value:.6g}"
            elif isinstance(value, bool):
                cell = "true" if value else "false"
            elif value is None:
                cell = ""
            else:
                cell = str(value)
            cells.append(cell)
        data_lines.append("| " + " | ".join(cells) + " |")

    return "\n".join([header, separator, *data_lines])


def load_config_from_env(env_var: str = "FUTURES_SELECTOR_CONFIG") -> SelectorConfig:
    """Load config from a JSON string stored in an environment variable."""
    payload = os.environ.get(env_var)
    if not payload:
        raise ValueError(f"Environment variable {env_var} is not set")
    return load_config(json.loads(payload))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Futures trend-following universe selector")
    parser.add_argument("--config", help="Path to YAML/JSON config file")
    parser.add_argument("--profile", help="Manifest profile name to load config from")
    parser.add_argument("--scanner-type", default="futures", help="Scanner type key in manifest (default: futures)")
    parser.add_argument("--limit", type=int, help="Override max results")
    parser.add_argument("--export", choices=["json", "csv"], help="Enable export and set type")
    parser.add_argument(
        "--export-enabled",
        action="store_true",
        help="Enable export of filtered results",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Return payloads without hitting TradingView",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable info-level logging")
    parser.add_argument(
        "--print-format",
        choices=["json", "table"],
        default="json",
        help="Format stdout as pretty JSON or markdown table",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    overrides: dict[str, Any] = {}
    if args.limit is not None:
        overrides["limit"] = args.limit
    if args.export is not None:
        overrides["export"] = {"enabled": True, "type": args.export}
    elif args.export_enabled:
        overrides["export"] = {"enabled": True}

    try:
        cfg = load_config(args.config, overrides=overrides, profile=args.profile, scanner_type=args.scanner_type)
    except (
        FileNotFoundError,
        ValidationError,
        ImportError,
        json.JSONDecodeError,
    ) as exc:  # pragma: no cover - CLI path
        logger.error("Failed to load config: %s", exc)
        return 1

    selector = FuturesUniverseSelector(cfg)
    result = selector.run(dry_run=args.dry_run)

    if args.print_format == "table" and result.get("status") != "dry_run":
        columns = result.get("filters_applied", {}).get("columns")
        table = _format_markdown_table(result.get("data") or [], columns)
        summary = [
            f"status: {result.get('status')}",
            f"total_candidates: {result.get('total_candidates')}",
            f"total_selected: {result.get('total_selected')}",
        ]
        if result.get("errors"):
            summary.append(f"errors: {result.get('errors')}")
        sys.stdout.write("\n".join(summary + [table]))
    else:
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True, default=str))

    sys.stdout.write("\n")
    return 0 if result.get("status") in {"success", "dry_run"} else 1


__all__ = [
    "FuturesUniverseSelector",
    "load_config",
    "load_config_from_env",
    "SelectorConfig",
    "main",
]


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
