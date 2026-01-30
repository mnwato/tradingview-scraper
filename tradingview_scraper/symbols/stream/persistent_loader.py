import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from tradingview_scraper.symbols.overview import Overview
from tradingview_scraper.symbols.stream import Streamer
from tradingview_scraper.symbols.stream.lakehouse import LakehouseStorage
from tradingview_scraper.symbols.stream.loader import DataLoader
from tradingview_scraper.symbols.stream.metadata import (
    DEFAULT_EXCHANGE_METADATA,
    DataProfile,
    ExchangeCatalog,
    MetadataCatalog,
    get_symbol_profile,
)

logger = logging.getLogger(__name__)


class PersistentDataLoader:
    """
    A wrapper for DataLoader that manages local persistence via LakehouseStorage.
    Encapsulates the forward-accumulation pattern to build deep history over time.
    """

    def __init__(self, lakehouse_path: str | Path | None = None, websocket_jwt_token: str = "unauthorized_user_token"):
        from tradingview_scraper.settings import get_settings

        settings = get_settings()

        path_str = str(lakehouse_path) if lakehouse_path else str(settings.lakehouse_dir)

        self.loader = DataLoader(websocket_jwt_token=websocket_jwt_token)
        self.storage = LakehouseStorage(base_path=path_str)
        self.catalog = MetadataCatalog(base_path=path_str)
        self.ex_catalog = ExchangeCatalog(base_path=path_str)
        self.overview = Overview()
        self.streamer = Streamer(export_result=False, websocket_jwt_token=websocket_jwt_token)

    def _ensure_metadata(self, symbol: str):
        """Checks if metadata exists, otherwise attempts to fetch it."""
        if self.catalog.get_instrument(symbol):
            return

        logger.info(f"Metadata missing for {symbol}. Triggering auto-enrichment...")
        try:
            # Fetch structural and descriptive metadata.
            # Timezone/session may be missing for some asset classes, so we resolve via exchange defaults.
            fields = [
                "pricescale",
                "minmov",
                "currency",
                "base_currency",
                "exchange",
                "type",
                "subtype",
                "description",
                "sector",
                "industry",
                "country",
                "timezone",
                "session",
            ]

            res = self.overview.get_symbol_overview(symbol, fields=fields)

            if res["status"] == "success":
                data = res["data"]

                exchange = data.get("exchange") or symbol.split(":", 1)[0]
                ex_defaults = DEFAULT_EXCHANGE_METADATA.get(exchange, {})

                pricescale = data.get("pricescale", 1) or 1
                minmov = data.get("minmov", 1) or 1

                tick_size = (minmov / pricescale) if pricescale else None

                # Hierarchy: API -> exchange defaults -> fallback
                timezone = data.get("timezone") or ex_defaults.get("timezone") or "UTC"

                # Persist profile for PIT-safe backtests
                profile = get_symbol_profile(symbol, {"type": data.get("type"), "is_crypto": ex_defaults.get("is_crypto")})

                session = data.get("session")
                if not session:
                    session = "24x7" if profile == DataProfile.CRYPTO else "Unknown"

                country = data.get("country") or ex_defaults.get("country")

                record = {
                    "symbol": symbol,
                    "exchange": exchange,
                    "base": data.get("base_currency"),
                    "quote": data.get("currency"),
                    "type": data.get("type"),
                    "subtype": data.get("subtype"),
                    "profile": profile.value,
                    "description": data.get("description"),
                    "sector": data.get("sector"),
                    "industry": data.get("industry"),
                    "country": country,
                    "pricescale": pricescale,
                    "minmov": minmov,
                    "tick_size": tick_size,
                    "timezone": timezone,
                    "session": session,
                    "active": True,
                }

                self.catalog.upsert_symbols([record])

                # Ensure exchange defaults are materialized.
                self.ex_catalog.upsert_exchange(
                    {
                        "exchange": exchange,
                        "timezone": ex_defaults.get("timezone") or timezone,
                        "is_crypto": bool(ex_defaults.get("is_crypto", False)),
                        "country": ex_defaults.get("country") or country or "Global",
                        "description": ex_defaults.get("description", f"{exchange} Exchange"),
                    }
                )
                logger.info(f"Metadata enriched for {symbol}.")
            else:
                logger.warning(f"Could not fetch metadata for {symbol}: {res.get('error')}")

        except Exception as e:
            logger.error(f"Failed to auto-enrich metadata for {symbol}: {e}")

    def sync(self, symbol: str, interval: str = "1h", depth: int = 1000, **kwargs) -> int:
        """
        Synchronizes local storage with the latest data from the API.
        Fetches the latest N candles and merges them into the lakehouse.

        Args:
            symbol (str): Symbol in 'EXCHANGE:SYMBOL' format.
            interval (str): Timeframe interval.
            depth (int): Number of candles to fetch for initial backfill or update.
            **kwargs: Extra arguments passed to Streamer.stream (e.g., timeout params).

        Returns:
            int: Number of new unique candles added.
        """
        # Ensure metadata exists before syncing data
        self._ensure_metadata(symbol)

        last_ts = self.storage.get_last_timestamp(symbol, interval)

        if last_ts:
            last_dt = datetime.fromtimestamp(last_ts)
            logger.info(f"Syncing {symbol} ({interval}) from last seen: {last_dt}")
        else:
            logger.info(f"Performing initial sync for {symbol} ({interval}) with depth {depth}")

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(minutes=self.loader.TIMEFRAME_MINUTES[interval] * depth)

        parts = symbol.split(":")
        res = self.streamer.stream(parts[0], parts[1], timeframe=interval, numb_price_candles=depth, auto_close=True, **kwargs)
        candles = res.get("ohlc", []) if isinstance(res, dict) else []

        if candles:
            count_before = len(self.storage.load_candles(symbol, interval))
            self.storage.save_candles(symbol, interval, candles)
            count_after = len(self.storage.load_candles(symbol, interval))
            new_records = count_after - count_before
            logger.info(f"Sync complete. Added {new_records} new candles.")
            return new_records

        return 0

    def repair(
        self,
        symbol: str,
        interval: str = "1h",
        max_depth: Optional[int] = None,
        max_fills: int = 5,
        max_time: float = 60.0,
        max_total_candles: int = 20000,
        profile: DataProfile = DataProfile.UNKNOWN,
        **kwargs,
    ) -> int:
        """
        Detects and attempts to fill gaps in local storage for a symbol.

        Args:
            max_fills (int): Maximum number of gaps to fill in one run to avoid chasing history.
            max_time (float): Maximum seconds to spend on one symbol's repair.
            max_total_candles (int): Maximum total candles to fill for one symbol.
            profile (DataProfile): Asset class profile for market-aware gap detection.
            **kwargs: Extra arguments passed to sync -> Streamer.stream.
        """
        # Determine if it's a crypto symbol for smarter gap detection
        if profile == DataProfile.UNKNOWN:
            meta = self.catalog.get_instrument(symbol)
            profile = get_symbol_profile(symbol, meta)

        gaps = self.storage.detect_gaps(symbol, interval, profile=profile)
        if not gaps:
            logger.info(f"No gaps detected for {symbol} ({interval}).")
            return 0

        total_filled = 0
        filled_count = 0
        start_time = datetime.now()

        # 2010 cutoff timestamp
        legacy_cutoff = datetime(2010, 1, 1).timestamp()

        # Fill gaps from newest to oldest.
        # This is more efficient because deeper syncs fill all subsequent gaps.
        # If a sync returns 0 new candles, we break early (genesis reached).
        for gap_start, gap_end in reversed(gaps):
            # Check caps
            if filled_count >= max_fills:
                logger.info(f"Reached max gap fill limit ({max_fills}) for {symbol}. Stopping repair.")
                break

            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed >= max_time:
                logger.warning(f"Reached max time limit ({max_time}s) for {symbol} repair. Stopping.")
                break

            if total_filled >= max_total_candles:
                logger.warning(f"Reached max total candles limit ({max_total_candles}) for {symbol}. Stopping.")
                break

            # Skip legacy gaps (pre-2010)
            if gap_end < legacy_cutoff:
                logger.info(f"Skipping legacy gap for {symbol}: {datetime.fromtimestamp(gap_start)} - {datetime.fromtimestamp(gap_end)}")
                continue

            # Redundancy check: see if gap was already filled by a previous deeper sync
            if self.storage.contains_timestamp(symbol, interval, gap_start):
                logger.info(f"Gap at {datetime.fromtimestamp(gap_start)} already filled. Skipping.")
                continue

            now_ts = datetime.now().timestamp()
            diff_mins = (now_ts - gap_start) / 60
            depth = int(diff_mins / self.loader.TIMEFRAME_MINUTES[interval]) + 5

            if depth > 8500:
                logger.warning(f"Gap at {datetime.fromtimestamp(gap_start)} is too deep ({depth} candles). Max reach is ~8500.")
                depth = 8500

            if max_depth and depth > max_depth:
                logger.info(f"Gap depth {depth} capped to limit {max_depth}.")
                depth = max_depth

            logger.info(f"Attempting to fill gap: {datetime.fromtimestamp(gap_start)} to {datetime.fromtimestamp(gap_end)} (Depth: {depth})")
            added = self.sync(symbol, interval, depth=depth, **kwargs)

            if added == 0:
                logger.info(f"Sync returned 0 new candles for {symbol} at depth {depth}. Assuming genesis reached. Stopping repair.")
                break

            total_filled += added
            filled_count += 1

        return total_filled

    def load(self, symbol: str, start: Union[datetime, str], end: Union[datetime, str], interval: str = "1h", force_api: bool = False) -> pd.DataFrame:
        """
        Loads data from local storage, falling back to API if range is missing.
        """
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)

        start_ts = start.timestamp()
        end_ts = end.timestamp()

        df = self.storage.load_candles(symbol, interval, start_ts, end_ts)

        if df.empty or force_api:
            logger.info(f"Data for {symbol} range not found in local storage. Fetching from API...")
            api_candles = self.loader.load(symbol, start, end, interval)
            if api_candles:
                self.storage.save_candles(symbol, interval, api_candles)
                df = self.storage.load_candles(symbol, interval, start_ts, end_ts)

        return df
