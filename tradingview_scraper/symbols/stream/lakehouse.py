import logging
import os
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from tradingview_scraper.symbols.stream.metadata import DataProfile, get_exchange_calendar

logger = logging.getLogger(__name__)


class LakehouseStorage:
    """
    Manages persistent storage for the Data Lakehouse using Parquet files.
    Standardizes on a single file per symbol/interval.
    """

    def __init__(self, base_path: str | Path | None = None):
        from tradingview_scraper.settings import get_settings

        settings = get_settings()
        self.base_path = Path(base_path) if base_path else settings.lakehouse_dir
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_path(self, symbol: str, interval: str) -> str:
        safe_symbol = symbol.replace(":", "_")
        return os.path.join(self.base_path, f"{safe_symbol}_{interval}.parquet")

    def save_candles(self, symbol: str, interval: str, candles: List[Dict]):
        """
        Saves candles to a Parquet file, merging with existing data.
        Duplicates are resolved by keeping the most recent record.
        """
        if not candles:
            return

        file_path = self._get_path(symbol, interval)
        new_df = pd.DataFrame(candles)

        if os.path.exists(file_path):
            existing_df = pd.read_parquet(file_path)
            combined_df = pd.concat([existing_df, new_df])
            # Keep the newest record for any given timestamp
            combined_df = combined_df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
        else:
            combined_df = new_df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")

        combined_df.to_parquet(file_path, index=False)

    def load_candles(
        self,
        symbol: str,
        interval: str,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Loads candles from a Parquet file for a given range.
        """
        file_path = self._get_path(symbol, interval)
        if not os.path.exists(file_path):
            return pd.DataFrame()

        df_raw = pd.read_parquet(file_path)

        # Filter range
        df_filtered = df_raw
        if start_ts:
            df_filtered = df_filtered[df_filtered["timestamp"] >= start_ts]
        if end_ts:
            df_filtered = df_filtered[df_filtered["timestamp"] <= end_ts]

        if not isinstance(df_filtered, pd.DataFrame):
            return pd.DataFrame()

        return df_filtered.sort_values("timestamp")

    def get_last_timestamp(self, symbol: str, interval: str) -> Optional[float]:
        """
        Returns the timestamp of the last available candle.
        """
        file_path = self._get_path(symbol, interval)
        if not os.path.exists(file_path):
            return None

        # Read only the timestamp column to optimize performance
        df = pd.read_parquet(file_path, columns=["timestamp"])
        if not df.empty:
            return float(df["timestamp"].max())
        return None

    def contains_timestamp(self, symbol: str, interval: str, timestamp: float) -> bool:
        """
        Efficiently checks if a specific timestamp exists in storage for a symbol.
        """
        file_path = self._get_path(symbol, interval)
        if not os.path.exists(file_path):
            return False

        # Read only the timestamp column to check existence
        df = pd.read_parquet(file_path, columns=["timestamp"])
        if df.empty:
            return False
        return timestamp in df["timestamp"].values

    def detect_gaps(self, symbol: str, interval: str, profile: DataProfile = DataProfile.UNKNOWN, start_ts: Optional[float] = None) -> List[tuple]:
        """
        Identifies missing data points in the historical time-series.

        Args:
            symbol (str): Symbol name.
            interval (str): Timeframe interval.
            profile (DataProfile): Asset class profile for market-aware filtering.
            start_ts (Optional[float]): Only check for gaps after this timestamp.

        Returns:
            List[tuple]: List of (start_missing_ts, end_missing_ts) gaps.
        """
        df = self.load_candles(symbol, interval, start_ts=start_ts)
        if df.empty or len(df) < 2:
            return []

        # Expected interval in seconds
        from tradingview_scraper.symbols.stream.loader import DataLoader

        interval_mins = DataLoader.TIMEFRAME_MINUTES.get(interval)
        if not interval_mins:
            logger.error(f"Unknown interval for gap detection: {interval}")
            return []

        expected_diff = interval_mins * 60
        gaps = []

        # Pre-load calendar for the specific symbol
        cal = get_exchange_calendar(symbol, profile)

        timestamps = df["timestamp"].tolist()
        for i in range(1, len(timestamps)):
            diff = timestamps[i] - timestamps[i - 1]
            if diff > expected_diff * 1.5:  # Allow some tolerance
                gap_start = timestamps[i - 1] + expected_diff
                gap_end = timestamps[i] - expected_diff

                # Market-aware filtering
                if profile != DataProfile.CRYPTO:
                    # Normalize timestamps to Market Day (Sunday 22:00 -> Monday)
                    # We add 4 hours to push late-night UTC starts into the next business day
                    from datetime import datetime as dt_obj

                    def to_market_dt(ts):
                        dt = dt_obj.fromtimestamp(ts)
                        if profile in [DataProfile.FOREX, DataProfile.FUTURES] and dt.hour >= 20:
                            dt += timedelta(hours=4)

                        ts_obj = pd.Timestamp(dt)
                        return ts_obj.date()

                    s_dt = to_market_dt(gap_start)
                    e_dt = to_market_dt(gap_end)

                    # Skip gaps if the market was closed according to its institutional schedule
                    if interval == "1d":
                        try:
                            # exchange_calendars expects naive dates or Timestamps
                            # use pd.Timestamp directly to avoid to_datetime ambiguity
                            s_raw = dt_obj.fromtimestamp(gap_start)
                            e_raw = dt_obj.fromtimestamp(gap_end)

                            from typing import Any

                            s_pd: Any = pd.Timestamp(s_raw)
                            e_pd: Any = pd.Timestamp(e_raw)

                            if hasattr(s_pd, "normalize"):
                                s_pd = s_pd.normalize()
                            if hasattr(e_pd, "normalize"):
                                e_pd = e_pd.normalize()

                            sessions = cal.sessions_in_range(s_pd, e_pd)

                            # INSTITUTIONAL TOLERANCE:
                            # Many exchanges have 'technical' sessions on bank holidays
                            # where TradingView (and other retail providers) don't provide data.
                            # If the gap is exactly 1 session, we treat it as an acceptable
                            # institutional dropout and DO NOT flag it as a health failure.
                            if len(sessions) == 1:
                                logger.info(f"Ignoring 1-session institutional gap for {symbol}: {s_pd.date()}")
                                continue

                            if len(sessions) == 0:
                                continue

                        except Exception:
                            pass

                gaps.append((gap_start, gap_end))

        if gaps:
            logger.info(f"Detected {len(gaps)} gaps for {symbol} ({interval}).")
        return gaps
