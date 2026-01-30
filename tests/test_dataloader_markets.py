import logging
import unittest
from datetime import datetime, timedelta

from tradingview_scraper.symbols.stream.loader import DataLoader


class TestDataLoaderMarkets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)
        cls.loader = DataLoader()
        # Define a 7-day window to ensure we cover open market hours for Stocks/Forex
        cls.end_dt = datetime.now()
        cls.start_dt = cls.end_dt - timedelta(days=7)
        cls.interval = "1h"

    def _verify_data(self, symbol, data):
        print(f"\n>>> Verifying {symbol} <<<")
        self.assertTrue(len(data) > 0, f"No data returned for {symbol}")

        first_candle = data[0]
        last_candle = data[-1]

        print(f"  Count: {len(data)}")
        print(f"  First: {datetime.fromtimestamp(first_candle['timestamp'])}")
        print(f"  Last:  {datetime.fromtimestamp(last_candle['timestamp'])}")

        # Verify required fields
        for field in ["timestamp", "open", "high", "low", "close", "volume"]:
            self.assertIn(field, first_candle, f"Missing {field} in {symbol} data")

    def test_crypto_market(self):
        symbol = "BINANCE:BTCUSDT"
        data = self.loader.load(symbol, self.start_dt, self.end_dt, self.interval)
        self._verify_data(symbol, data)

    def test_forex_market(self):
        symbol = "FX_IDC:EURUSD"
        data = self.loader.load(symbol, self.start_dt, self.end_dt, self.interval)
        self._verify_data(symbol, data)

    def test_stock_market(self):
        symbol = "NASDAQ:AAPL"
        data = self.loader.load(symbol, self.start_dt, self.end_dt, self.interval)
        self._verify_data(symbol, data)

    def test_index_market(self):
        symbol = "SP:SPX"
        data = self.loader.load(symbol, self.start_dt, self.end_dt, self.interval)
        self._verify_data(symbol, data)

    def test_commodity_market(self):
        symbol = "COMEX:GC1!"
        data = self.loader.load(symbol, self.start_dt, self.end_dt, self.interval)
        self._verify_data(symbol, data)

    def test_non_standard_resolutions(self):
        # 3m and 3h were discovered in research
        symbol = "BINANCE:BTCUSDT"

        print("\n>>> Testing 3m resolution <<<")
        # Load last hour of 3m data
        start_3m = datetime.now() - timedelta(hours=1)
        end_3m = datetime.now()
        data_3m = self.loader.load(symbol, start_3m, end_3m, "3m")
        self.assertTrue(len(data_3m) > 0)

        print("\n>>> Testing 3h resolution <<<")
        # Load last day of 3h data
        start_3h = datetime.now() - timedelta(days=1)
        end_3h = datetime.now()
        data_3h = self.loader.load(symbol, start_3h, end_3h, "3h")
        self.assertTrue(len(data_3h) > 0)


if __name__ == "__main__":
    unittest.main()
