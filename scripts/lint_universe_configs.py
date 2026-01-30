from __future__ import annotations

import argparse
import glob
import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from pydantic import ValidationError

from tradingview_scraper.futures_universe_selector import DEFAULT_MOMENTUM, SelectorConfig

yaml: ModuleType | None
try:
    import yaml as _yaml
except Exception:  # pragma: no cover
    yaml = None
else:
    yaml = _yaml


@dataclass(frozen=True)
class LintIssue:
    level: str  # "ERROR" | "WARN"
    code: str
    path: Path
    message: str


REQUIRED_COLUMNS: List[str] = ["name", "close", "volume", "change", "Recommend.All"]


def _merge(base: Dict[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_mapping(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))

    ext = path.suffix.lower()
    text = path.read_text(encoding="utf-8")

    if ext in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML configs")
        payload = yaml.safe_load(text) or {}
    elif ext == ".json":
        payload = json.loads(text) or {}
    else:
        raise ValueError(f"Unsupported config extension: {path}")

    if not isinstance(payload, dict):
        raise ValueError(f"Config root must be a mapping/dict: {path}")

    return payload


def _resolve_with_presets(path: Path, stack: Tuple[Path, ...]) -> Dict[str, Any]:
    path = path.resolve()
    if path in stack:
        chain = " -> ".join(str(p) for p in (stack + (path,)))
        raise ValueError(f"base_preset cycle detected: {chain}")

    raw = _load_mapping(path)
    preset = raw.pop("base_preset", None)
    if preset:
        preset_path = Path(preset)
        if not preset_path.is_absolute():
            preset_path = (path.parent / preset_path).resolve()

        base = _resolve_with_presets(preset_path, stack + (path,))
        raw = _merge(base, raw)

    return raw


def _build_effective_columns(config: SelectorConfig) -> List[str]:
    columns: List[str] = []
    for col in REQUIRED_COLUMNS + (config.columns or []):
        if col not in columns:
            columns.append(col)

    for screen in [config.trend_screen, config.confirm_screen, config.execute_screen]:
        if not screen:
            continue

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

    if config.volume.value_traded_min > 0 and "Value.Traded" not in columns:
        columns.append("Value.Traded")

    if config.market_cap_floor is not None and "market_cap_calc" not in columns:
        columns.append("market_cap_calc")

    if config.trend.timeframe in {"daily", "weekly"} and "Perf.W" not in columns:
        columns.append("Perf.W")

    if config.momentum_composite_fields:
        composite_field = config.momentum_composite_field_name or "momentum_zscore"
        if composite_field and composite_field not in columns:
            columns.append(composite_field)

    return columns


def _lint_config(path: Path, strict: bool) -> List[LintIssue]:
    issues: List[LintIssue] = []

    try:
        raw = _resolve_with_presets(path, stack=())
    except Exception as exc:
        return [LintIssue("ERROR", "CFG_LOAD", path, str(exc))]

    try:
        config = SelectorConfig.model_validate(raw)
    except ValidationError as exc:
        return [LintIssue("ERROR", "CFG_SCHEMA", path, str(exc))]

    # --- Path checks ---
    base_dir = path.parent

    for symfile in config.include_symbol_files:
        sym_path = Path(symfile)
        if not sym_path.is_absolute():
            sym_path = base_dir / sym_path
        if not sym_path.exists():
            issues.append(LintIssue("ERROR", "CFG_SYMBOL_FILE", path, f"include_symbol_files missing: {symfile}"))

    if config.market_cap_file:
        cap_path = Path(config.market_cap_file)
        if not cap_path.is_absolute():
            cap_path = Path.cwd() / cap_path
        if not cap_path.exists():
            issues.append(LintIssue("WARN", "CFG_MARKET_CAP_FILE", path, f"market_cap_file not found: {config.market_cap_file}"))

    # --- Contradictions / dead config ---
    def _bool_attr(name: str) -> bool:
        # Linter must stay compatible with evolving SelectorConfig schemas.
        # Some fields exist only in older configs and are ignored by the model;
        # we treat them as disabled to avoid crashing the lint pass.
        return bool(getattr(config, name, False))

    if _bool_attr("include_perps_only") and _bool_attr("exclude_perps"):
        issues.append(LintIssue("ERROR", "CFG_CONTRADICTION_PERPS", path, "include_perps_only=true conflicts with exclude_perps=true"))

    if _bool_attr("include_dated_futures_only") and _bool_attr("exclude_dated_futures"):
        issues.append(LintIssue("ERROR", "CFG_CONTRADICTION_DATED", path, "include_dated_futures_only=true conflicts with exclude_dated_futures=true (universe will be empty)"))

    if config.include_stable_bases and config.exclude_stable_bases:
        issues.append(LintIssue("ERROR", "CFG_CONTRADICTION_STABLE", path, "include_stable_bases=true conflicts with exclude_stable_bases=true"))

    if config.group_duplicates and not config.dedupe_by_symbol:
        issues.append(LintIssue("WARN", "CFG_DEAD_GROUP_DUPES", path, "group_duplicates=true has no effect unless dedupe_by_symbol=true"))

    if _bool_attr("prefer_perps") and _bool_attr("exclude_perps"):
        issues.append(LintIssue("WARN", "CFG_DEAD_PREFER_PERPS", path, "prefer_perps=true has no effect when exclude_perps=true"))

    if config.attach_perp_counterparts and _bool_attr("exclude_perps"):
        issues.append(
            LintIssue(
                "WARN",
                "CFG_DEAD_ATTACH_PERPS",
                path,
                "attach_perp_counterparts=true is ineffective when exclude_perps=true (no perps remain to attach)",
            )
        )

    # --- Filter sanity checks ---
    for idx, flt in enumerate(config.filters or []):
        if not isinstance(flt, Mapping):
            issues.append(LintIssue("ERROR", "CFG_FILTER_SHAPE", path, f"filters[{idx}] must be a mapping"))
            continue

        left = flt.get("left")
        op = flt.get("operation")

        if not left or not isinstance(left, str):
            issues.append(LintIssue("ERROR", "CFG_FILTER_LEFT", path, f"filters[{idx}] missing string 'left'"))
            continue

        if not op or not isinstance(op, str):
            issues.append(LintIssue("ERROR", "CFG_FILTER_OP", path, f"filters[{idx}] missing string 'operation'"))
            continue

        if left == "index":
            issues.append(
                LintIssue(
                    "ERROR",
                    "CFG_FILTER_INDEX",
                    path,
                    "TradingView screener field 'index' is unstable (HTTP 400 Unknown field); prefer include_symbol_files",
                )
            )

    # --- Column/field coherence ---
    effective_columns = set(_build_effective_columns(config))

    def _flag_field(field: Optional[str], level: str, code: str, message: str) -> None:
        if not field:
            return
        if field not in effective_columns:
            issues.append(LintIssue(level, code, path, message))

    # Note: TradingView can sort server-side without returning `sort_by` in columns.
    # We only require the field if downstream logic needs the values (e.g. dedupe tie-breaks).
    if config.dedupe_by_symbol and not config.final_sort_by:
        _flag_field(config.sort_by, "WARN", "CFG_SORT_FIELD", f"sort_by '{config.sort_by}' not present in effective columns")

    _flag_field(
        config.final_sort_by,
        "ERROR",
        "CFG_FINAL_SORT_FIELD",
        f"final_sort_by '{config.final_sort_by}' not present in effective columns",
    )

    if config.base_universe_limit:
        _flag_field(
            config.base_universe_sort_by,
            "WARN",
            "CFG_BASE_SORT_FIELD",
            f"base_universe_sort_by '{config.base_universe_sort_by}' not present in effective columns",
        )

    for field in config.momentum_composite_fields:
        if field and field not in effective_columns:
            issues.append(LintIssue("WARN", "CFG_MOMENTUM_FIELD", path, f"momentum_composite_fields contains '{field}' not in columns"))

    # Trend horizons (mirror selector runtime defaults to avoid false positives)
    if config.trend.momentum.enabled:
        horizons = config.trend.momentum.horizons or {}
        if horizons == DEFAULT_MOMENTUM:
            if config.trend.timeframe == "daily":
                horizons = {"change": 0.0, "Perf.W": 0.0}
            elif config.trend.timeframe == "weekly":
                horizons = {"Perf.W": 0.0}
        if not horizons:
            if config.trend.timeframe == "daily":
                horizons = {"change": 0.0, "Perf.W": 0.0}
            elif config.trend.timeframe == "weekly":
                horizons = {"Perf.W": 0.0}
            else:
                horizons = DEFAULT_MOMENTUM

        for field in horizons.keys():
            if field and field not in effective_columns:
                issues.append(LintIssue("ERROR", "CFG_TREND_FIELD", path, f"trend horizon field '{field}' not in columns"))

    if config.trend.confirmation_momentum.enabled:
        for field in (config.trend.confirmation_momentum.horizons or {}).keys():
            if field and field not in effective_columns:
                issues.append(LintIssue("ERROR", "CFG_TREND_FIELD", path, f"trend horizon field '{field}' not in columns"))

    # Screen horizons
    for screen in [config.trend_screen, config.confirm_screen, config.execute_screen]:
        if not screen:
            continue
        if screen.momentum.enabled:
            for field in (screen.momentum.horizons or {}).keys():
                if field and field not in effective_columns:
                    issues.append(LintIssue("ERROR", "CFG_SCREEN_FIELD", path, f"screen horizon field '{field}' not in columns"))

    if strict:
        strict_issues = [LintIssue("ERROR", "STRICT", issue.path, f"{issue.code}: {issue.message}") for issue in issues if issue.level == "WARN"]
        issues.extend(strict_issues)

    return issues


def iter_config_files(configs_dir: Path) -> Iterable[Path]:
    yield from sorted(configs_dir.rglob("*.yaml"))
    yield from sorted(configs_dir.rglob("*.yml"))


def _iter_paths(paths: List[str]) -> Iterable[Path]:
    for raw in paths:
        # Support globs (e.g. configs/base/universes/binance*.yaml)
        if any(ch in raw for ch in ["*", "?", "[", "]"]):
            for match in sorted(glob.glob(raw, recursive=True)):
                yield Path(match)
            continue

        yield Path(raw)


def iter_config_files_from_args(configs_dir: Path, paths: Optional[List[str]]) -> Iterable[Path]:
    if not paths:
        yield from iter_config_files(configs_dir)
        return

    resolved: List[Path] = []
    for candidate in _iter_paths(paths):
        if candidate.is_dir():
            resolved.extend(list(iter_config_files(candidate)))
        elif candidate.is_file():
            if candidate.suffix.lower() in {".yaml", ".yml"}:
                resolved.append(candidate)
        else:
            # Ignore missing glob expansions; explicit non-existent paths should be surfaced.
            raise FileNotFoundError(str(candidate))

    seen = set()
    for path in sorted((p.resolve() for p in resolved), key=lambda p: str(p)):
        if path not in seen:
            seen.add(path)
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint TradingView universe selector configs")
    parser.add_argument("--configs-dir", default="configs", help="Config directory root (default: configs)")
    parser.add_argument("--path", action="append", help="File/dir/glob to lint (repeatable). Overrides --configs-dir discovery.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    configs_dir = Path(args.configs_dir)
    if not configs_dir.exists():
        print(f"configs dir not found: {configs_dir}")
        return 2

    all_issues: List[LintIssue] = []
    try:
        paths = list(iter_config_files_from_args(configs_dir, args.path))
    except FileNotFoundError as exc:
        print(f"configs path not found: {exc}")
        return 2

    for path in paths:
        all_issues.extend(_lint_config(path, strict=args.strict))

    errors = [i for i in all_issues if i.level == "ERROR"]
    warnings = [i for i in all_issues if i.level == "WARN"]

    for issue in all_issues:
        print(f"{issue.level} {issue.code} {issue.path}: {issue.message}")

    if errors:
        print(f"\nFound {len(errors)} errors, {len(warnings)} warnings")
        return 1

    print(f"\nOK: {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
