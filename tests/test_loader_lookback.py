import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from tradingview_scraper.symbols.stream.loader import DataLoader


class TestDataLoaderLookbackWindow(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()

    def test_caps_intraday_candles(self):
        start = datetime.now() - timedelta(days=5 * 365)
        end = datetime.now()

        candles = self.loader._calculate_candles_needed(start, end, "1h")

        self.assertEqual(candles, self.loader.GENESIS_CANDLE_LIMITS["1h"])

    def test_recent_request_not_capped(self):
        start = datetime.now() - timedelta(hours=12)
        end = datetime.now()

        candles = self.loader._calculate_candles_needed(start, end, "1m")

        self.assertLess(candles, self.loader.GENESIS_CANDLE_LIMITS["1m"])
        self.assertGreaterEqual(candles, 10)

    @patch("tradingview_scraper.symbols.stream.loader.Streamer")
    def test_probe_limits_short_history(self, mock_streamer_cls):
        now = datetime.now()
        start = now - timedelta(days=100)
        end = now

        available_candles = [{"timestamp": int((end - timedelta(days=i)).timestamp()), "open": 1, "high": 1, "low": 1, "close": 1} for i in range(42)]

        mock_streamer = MagicMock()
        mock_streamer.stream.return_value = {"ohlc": available_candles}
        mock_streamer_cls.return_value = mock_streamer

        data = self.loader.load("BYBIT:CCUSDT", start, end, "1d")

        self.assertEqual(len(data), len(available_candles))
        self.assertEqual(mock_streamer.stream.call_count, 1)
        self.assertEqual(mock_streamer.stream.call_args[1]["numb_price_candles"], self.loader.PROBE_CANDLE_LIMIT)


if __name__ == "__main__":
    unittest.main()
