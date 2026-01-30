from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("pipelines.selection")


class SelectionContext(BaseModel):
    """
    The state container for the Selection Pipeline.
    Passes through each stage, accumulating features and decisions.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str
    trace_id: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

    # Stage 1: Ingestion
    raw_pool: List[Dict[str, Any]] = Field(default_factory=list)
    returns_df: pd.DataFrame = Field(default_factory=pd.DataFrame)

    # Stage 2: Feature Engineering
    feature_store: pd.DataFrame = Field(default_factory=pd.DataFrame)

    # Stage 3: Inference
    inference_outputs: pd.DataFrame = Field(default_factory=pd.DataFrame)
    model_metadata: Dict[str, Any] = Field(default_factory=dict)

    # Stage 4: Partitioning
    clusters: Dict[int, List[str]] = Field(default_factory=dict)

    # Stage 5: Policy Pruning
    winners: List[Dict[str, Any]] = Field(default_factory=list)

    # Stage 6: Synthesis
    strategy_atoms: List[Any] = Field(default_factory=list)  # List[StrategyAtom]
    composition_map: Dict[str, Dict[str, float]] = Field(default_factory=dict)

    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)

    def log_event(self, stage: str, event: str, data: Optional[Dict[str, Any]] = None):
        self.audit_trail.append({"stage": stage, "event": event, "data": data or {}})


class BasePipelineStage(ABC):
    """
    Abstract Base Class for all Pipeline Stages.
    Ensures statelessness and consistent interfaces.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Friendly name of the stage."""
        pass

    @abstractmethod
    def execute(self, context: SelectionContext) -> SelectionContext:
        """
        Main execution logic for the stage.
        Must return the modified (enriched) context.
        """
        pass


class IngestionValidator:
    """
    L1 Data Contract Validator.
    Enforces institutional standards: Toxicity bounds and 'No Padding'.
    """

    @staticmethod
    def validate_returns(df: pd.DataFrame, strict: bool = False) -> List[str]:
        """
        Validates returns matrix against toxicity and padding rules.
        Uses Pandera for formal schema enforcement (Phase 620).
        """
        from tradingview_scraper.pipelines.contracts import ReturnsSchema
        import pandera as pa

        if df.empty:
            return []

        try:
            # 1. Formal Schema Validation (Bounds, Index, Types)
            ReturnsSchema.validate(df)
        except pa.errors.SchemaError as e:
            logger.warning(f"Data Contract Violation in returns_matrix: {e}")
            if strict:
                raise

        failed_symbols = []
        for col in df.columns:
            series = df[col]
            # ... (Existing heuristic checks for padding) ...

            # 2. 'No Padding' Compliance (TradFi only)
            # Heuristic: If EXCHANGE is not BINANCE/OKX/etc, check weekends
            if ":" in str(col):
                exchange = str(col).split(":")[0].upper()
                is_crypto = exchange in ["BINANCE", "OKX", "BYBIT", "BITGET", "KUCOIN", "COINBASE", "KRAKEN"]

                if not is_crypto:
                    # Check for 0.0 exactly on weekends
                    # Use robust dayofweek check
                    try:
                        # Extract the dayofweek from the index
                        index_dt = pd.to_datetime(df.index)
                        # Use list comprehension to avoid DatetimeIndex/Index confusion in LSP
                        days = [t.dayofweek for t in index_dt]
                        weekends_mask = [d >= 5 for d in days]

                        if any(weekends_mask):
                            # Filter series
                            weekend_vals = series.iloc[weekends_mask].dropna()
                            if not weekend_vals.empty and (weekend_vals == 0.0).all():
                                logger.warning(f"IngestionValidator: {col} failed 'No Padding' standard (Zeroes found on weekends)")
                                failed_symbols.append(str(col))
                                continue
                    except Exception as e:
                        logger.warning(f"IngestionValidator: Could not check weekends for {col}: {e}")

        return failed_symbols


class AdvancedToxicityValidator:
    """
    Advanced Microstructure Toxicity Validator.
    Detects Volume Spikes and Price Stalls.
    """

    @staticmethod
    def is_volume_toxic(volume: pd.Series, sigma_threshold: float = 10.0) -> bool:
        """Detects if the latest volume bar is a statistical outlier (> 10 sigma)."""
        if len(volume) < 21:
            return False

        # Calculate trailing statistics (excluding latest)
        trailing = volume.iloc[:-1]
        mean_v = trailing.mean()
        std_v = trailing.std()

        if std_v == 0:
            return float(volume.iloc[-1]) > float(mean_v) * 2  # Simple multiplier fallback

        z_score = (float(volume.iloc[-1]) - float(mean_v)) / float(std_v)
        return bool(z_score > sigma_threshold)

    @staticmethod
    def is_price_stalled(prices: pd.Series, threshold: int = 3) -> bool:
        """Detects if price has been perfectly flat for N consecutive bars."""
        if len(prices) < threshold + 1:
            return False

        # Calculate diffs
        diffs = prices.diff().dropna()
        recent_diffs = diffs.tail(threshold)

        # If ALL recent diffs are EXACTLY zero
        return bool((recent_diffs == 0).all())


class FoundationHealthRegistry:
    """
    Manages the persistent health ledger for Lakehouse assets.
    """

    def __init__(self, path: Optional[Path] = None):
        from tradingview_scraper.settings import get_settings

        self.path = path or (get_settings().lakehouse_dir / "foundation_health.json")
        self.data: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load health registry: {e}")
                self.data = {}

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save health registry: {e}")

    def update_status(self, symbol: str, status: str, **metrics):
        self.data[symbol] = {
            "status": status,
            "last_audit": datetime.now().isoformat(),
            **metrics,
        }

    def is_healthy(self, symbol: str) -> bool:
        return self.data.get(symbol, {}).get("status") == "healthy"
