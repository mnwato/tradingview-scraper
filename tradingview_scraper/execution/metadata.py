import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExecutionLimits:
    symbol: str
    venue: str
    lot_size: float
    min_notional: float
    step_size: float
    tick_size: float
    maker_fee: float
    taker_fee: float
    contract_size: float
    updated_at: pd.Timestamp


class MissingMetadataError(Exception):
    """Raised when execution limits are missing in strict mode."""

    pass


class ExecutionMetadataCatalog:
    """
    Manages venue-specific execution limits (lot_size, min_notional, step_size).
    Ensures parity between backtests and live execution.
    """

    REQUIRED_COLS = ["symbol", "venue", "lot_size", "min_notional", "step_size", "tick_size", "maker_fee", "taker_fee", "contract_size", "updated_at"]

    def __init__(self, base_path: str | Path | None = None):
        from tradingview_scraper.settings import get_settings

        settings = get_settings()

        self.base_path = Path(base_path) if base_path else settings.lakehouse_dir
        self.catalog_path = self.base_path / "execution.parquet"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._df = self._load_catalog()
        if not os.path.exists(self.catalog_path):
            self.save()

    def _load_catalog(self) -> pd.DataFrame:
        """Loads the execution catalog from disk or returns an empty DataFrame."""
        if os.path.exists(self.catalog_path):
            try:
                df = pd.read_parquet(self.catalog_path)
                for col in self.REQUIRED_COLS:
                    if col not in df.columns:
                        df[col] = None
                return cast(pd.DataFrame, df[self.REQUIRED_COLS])
            except Exception as e:
                logger.error(f"Failed to load execution catalog: {e}")

        return pd.DataFrame(columns=pd.Index(self.REQUIRED_COLS))

    def get_limits(self, symbol: str, venue: str, strict: bool = False) -> Optional[ExecutionLimits]:
        """
        Retrieves execution limits for a specific symbol and venue.

        Args:
            symbol: Unified symbol key (e.g., BINANCE:BTCUSDT)
            venue: Venue name (e.g., BINANCE, IBKR)
            strict: If True, raises MissingMetadataError if not found.
        """
        if self._df.empty:
            if strict:
                raise MissingMetadataError(f"No execution metadata found for {symbol} on {venue} (Empty Catalog)")
            return None

        mask = (self._df["symbol"] == symbol) & (self._df["venue"] == venue)
        match = self._df[mask]

        if match.empty:
            if strict:
                raise MissingMetadataError(f"Execution metadata missing for {symbol} on {venue}")
            return None

        row = match.iloc[0]

        # Handle Timestamp cast carefully to satisfy type checkers
        updated_at_val = row["updated_at"]
        updated_at: pd.Timestamp
        if pd.isna(updated_at_val):
            updated_at = pd.Timestamp.now()
        else:
            updated_at = pd.Timestamp(updated_at_val)

        return ExecutionLimits(
            symbol=str(row["symbol"]),
            venue=str(row["venue"]),
            lot_size=float(row["lot_size"]) if not pd.isna(row["lot_size"]) else 0.0,
            min_notional=float(row["min_notional"]) if not pd.isna(row["min_notional"]) else 0.0,
            step_size=float(row["step_size"]) if not pd.isna(row["step_size"]) else 0.0,
            tick_size=float(row["tick_size"]) if not pd.isna(row["tick_size"]) else 0.0,
            maker_fee=float(row["maker_fee"]) if not pd.isna(row["maker_fee"]) else 0.0,
            taker_fee=float(row["taker_fee"]) if not pd.isna(row["taker_fee"]) else 0.0,
            contract_size=float(row["contract_size"]) if not pd.isna(row["contract_size"]) else 1.0,
            updated_at=updated_at,
        )

    def upsert_limits(self, limits_data: List[Dict[str, Any]]):
        """Inserts or updates execution limits."""
        if not limits_data:
            return

        new_df = pd.DataFrame(limits_data)
        for col in self.REQUIRED_COLS:
            if col not in new_df.columns:
                new_df[col] = None

        new_df["updated_at"] = pd.Timestamp.now()

        if self._df.empty:
            self._df = new_df[self.REQUIRED_COLS]
        else:
            # Merge and keep last (most recent update)
            self._df = pd.concat([self._df, new_df[self.REQUIRED_COLS]]).drop_duplicates(subset=["symbol", "venue"], keep="last")

        self.save()

    def save(self):
        """Persists the catalog to disk."""
        self._df.to_parquet(self.catalog_path, index=False)
        logger.info(f"Execution metadata catalog saved with {len(self._df)} entries.")


def cast(t: Any, x: Any) -> Any:
    return x
