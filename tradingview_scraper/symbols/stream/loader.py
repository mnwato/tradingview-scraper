import logging
from datetime import datetime, timedelta
from typing import List, Optional, Union

from tradingview_scraper.symbols.exceptions import DataNotFoundError
from tradingview_scraper.symbols.stream import Streamer
from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

logger = logging.getLogger(__name__)


class DataLoader:
    """
    A class to load historical data for backtesting using the Streamer API.
    Provides a standardized interface: load(symbol, start, end, interval).
    """

    TIMEFRAME_MINUTES = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "45m": 45, "1h": 60, "2h": 120, "3h": 180, "4h": 240, "1d": 1440, "1w": 10080, "1M": 43200}
    GENESIS_CANDLE_LIMITS = {"1m": 8500, "3m": 8500, "5m": 8500, "15m": 8500, "30m": 8500, "45m": 8500, "1h": 8500, "2h": 8500, "3h": 8500, "4h": 8500, "1d": 3050, "1w": 3050, "1M": 3050}
    DEFAULT_GENESIS_CAP = 8500
    PROBE_CANDLE_LIMIT = 50

    def __init__(
        self,
        websocket_jwt_token: str = "unauthorized_user_token",
        export_result: bool = True,
        idle_timeout_seconds: float = 5.0,
        idle_packet_limit: int = 3,
    ):
        self.websocket_jwt_token = websocket_jwt_token
        self.export_result = export_result
        self.idle_timeout_seconds = idle_timeout_seconds
        self.idle_packet_limit = idle_packet_limit

        self.catalog = MetadataCatalog()
        self.streamer: Optional[Streamer] = None

    def _get_streamer(self) -> Streamer:
        if self.streamer is None:
            self.streamer = Streamer(
                export_result=self.export_result,
                websocket_jwt_token=self.websocket_jwt_token,
                idle_timeout_seconds=self.idle_timeout_seconds,
                idle_packet_limit=self.idle_packet_limit,
            )
        assert self.streamer is not None
        return self.streamer

    def _calculate_candles_needed(self, start: datetime, end: datetime, interval: str, exchange_symbol: Optional[str] = None) -> int:
        """
        Calculates the number of candles needed to cover the range from start to end.
        Caps the lookback so we never request more candles than the API can serve for this symbol/timeframe.
        For symbols with less than one month of history, uses a conservative limit.
        """
        if interval not in self.TIMEFRAME_MINUTES:
            raise ValueError(f"Unsupported interval: {interval}")

        # We need to calculate how many 'interval' units are between 'now' and 'start'
        # because the API returns the latest N candles.
        now = datetime.now()
        delta = now - start

        minutes_total = delta.total_seconds() / 60
        candles_count = int(minutes_total / self.TIMEFRAME_MINUTES[interval])
        candles_count = max(candles_count + 10, 10)

        # Cap based on known genesis timestamp if available
        if exchange_symbol:
            meta = self.catalog.get_instrument(exchange_symbol)
            # Check if genesis_ts exists and is valid (not None and not NaN)
            genesis_ts = meta.get("genesis_ts") if meta else None

            # Use pandas isna if available or simple check
            genesis_val: Optional[float] = None
            if isinstance(genesis_ts, (int, float)):
                try:
                    genesis_val = float(genesis_ts)
                except (ValueError, TypeError):
                    genesis_val = None
            elif genesis_ts is not None:
                try:
                    import math

                    gv = float(genesis_ts)
                    if not math.isnan(gv) and gv > 0:
                        genesis_val = gv
                except (ValueError, TypeError):
                    genesis_val = None

            if genesis_val is not None:
                assert genesis_val is not None
                genesis_dt = datetime.fromtimestamp(float(genesis_val))

                # If requested start is before genesis, we are bounded by genesis
                # But candles_count is from NOW.
                # So max candles = (now - genesis) / interval

                max_minutes = (now - genesis_dt).total_seconds() / 60
                max_available = int(max_minutes / self.TIMEFRAME_MINUTES[interval])
                # Add a small buffer for safety/rounding
                max_available += 5

                if candles_count > max_available:
                    logger.info("Capping candle request for %s based on genesis %s: %s -> %s", exchange_symbol, genesis_dt.strftime("%Y-%m-%d"), candles_count, max_available)
                    return max_available

        # Check if the requested start date is less than one month ago
        # If so, use a conservative cap to avoid requesting more data than available
        one_month_ago = now - timedelta(days=30)
        if start > one_month_ago:
            # For symbols with recent start dates (less than 1 month history),
            # cap the request to avoid over-requesting
            conservative_cap = min(self.PROBE_CANDLE_LIMIT, candles_count)
            if candles_count > conservative_cap:
                logger.info(
                    "Symbol has recent start date (%s), capping candle request from %s to %s for interval %s.",
                    start.strftime("%Y-%m-%d"),
                    candles_count,
                    conservative_cap,
                    interval,
                )
                return conservative_cap

        cap = self.GENESIS_CANDLE_LIMITS.get(interval, self.DEFAULT_GENESIS_CAP)
        if candles_count > cap:
            capped_start = now - timedelta(minutes=self.TIMEFRAME_MINUTES[interval] * cap)
            logger.info(
                "Capping candle request from %s to %s for interval %s (approx earliest reachable start %s).",
                candles_count,
                cap,
                interval,
                capped_start,
            )
            return cap

        return candles_count

    def _stream_with_retry(self, streamer: Streamer, exchange: str, symbol: str, interval: str, n_candles: int) -> List[dict]:
        try:
            res = streamer.stream(exchange, symbol, timeframe=interval, numb_price_candles=n_candles, auto_close=True)
            return res.get("ohlc", []) if isinstance(res, dict) else []
        except DataNotFoundError as e:
            logger.warning(f"No OHLC data for {exchange}:{symbol} on first attempt: {e}. Retrying with smaller window.")
            try:
                retry_candles = max(20, n_candles // 2)
                res = streamer.stream(exchange, symbol, timeframe=interval, numb_price_candles=retry_candles, auto_close=True)
                return res.get("ohlc", []) if isinstance(res, dict) else []
            except Exception as e_retry:
                logger.error(f"Retry failed for {exchange}:{symbol}: {e_retry}")
                return []
        except Exception as e:
            logger.error(f"Failed to load historical data for {exchange}:{symbol}: {e}")
            return []

    def load(self, exchange_symbol: str, start: Union[datetime, str], end: Union[datetime, str], interval: str = "1h") -> List[dict]:
        """
        Loads historical OHLCV data for a specific range.

        Args:
            exchange_symbol (str): Symbol in 'EXCHANGE:SYMBOL' format.
            start (datetime | str): Start date.
            end (datetime | str): End date.
            interval (str): Timeframe interval (e.g., '1m', '1h', '1d').

        Returns:
            List[dict]: List of OHLCV candles within the requested range.
        """
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)

        parts = exchange_symbol.split(":")
        if len(parts) != 2:
            raise ValueError("Symbol must be in 'EXCHANGE:SYMBOL' format")

        exchange, symbol = parts[0], parts[1]

        n_candles = self._calculate_candles_needed(start, end, interval, exchange_symbol=exchange_symbol)
        logger.info(f"Requesting {n_candles} candles for {exchange_symbol} to cover range starting {start}")

        probe_n = min(n_candles, self.PROBE_CANDLE_LIMIT)
        streamer = self._get_streamer()
        candles = self._stream_with_retry(streamer, exchange, symbol, interval, probe_n)

        if len(candles) < probe_n:
            logger.info(
                "Reducing candle request for %s (%s) from %s to %s based on available history (probe returned %s).",
                exchange_symbol,
                interval,
                n_candles,
                len(candles),
                len(candles),
            )
            n_candles = len(candles)
        elif n_candles > probe_n:
            candles = self._stream_with_retry(streamer, exchange, symbol, interval, n_candles)

        start_ts = start.timestamp()
        end_ts = end.timestamp()
        filtered = [c for c in candles if start_ts <= c["timestamp"] <= end_ts]

        logger.info(f"Fetched {len(candles)} total, returned {len(filtered)} within range.")
        return filtered


if __name__ == "__main__":
    # Quick demo
    logging.basicConfig(level=logging.INFO)
    loader = DataLoader()

    # Load last 24 hours of 1h data
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=1)

    data = loader.load("BINANCE:BTCUSDT", start_dt, end_dt, interval="1h")
    for candle in data[:5]:
        print(datetime.fromtimestamp(candle["timestamp"]), candle["close"])
