import os
import shutil
import unittest

from tradingview_scraper.symbols.stream.lakehouse import LakehouseStorage


class TestLakehouseStorage(unittest.TestCase):
    def setUp(self):
        self.test_dir = "data/test_lakehouse"
        self.storage = LakehouseStorage(base_path=self.test_dir)
        self.symbol = "TEST:SYM"
        self.interval = "1h"

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_and_load(self):
        candles = [{"timestamp": 1000, "open": 10, "high": 12, "low": 9, "close": 11, "volume": 100}, {"timestamp": 2000, "open": 11, "high": 13, "low": 10, "close": 12, "volume": 200}]
        self.storage.save_candles(self.symbol, self.interval, candles)

        df = self.storage.load_candles(self.symbol, self.interval)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["timestamp"], 1000)

    def test_deduplication(self):
        candles_1 = [{"timestamp": 1000, "close": 11}]
        candles_2 = [{"timestamp": 1000, "close": 11}, {"timestamp": 2000, "close": 12}]

        self.storage.save_candles(self.symbol, self.interval, candles_1)
        self.storage.save_candles(self.symbol, self.interval, candles_2)

        df = self.storage.load_candles(self.symbol, self.interval)
        self.assertEqual(len(df), 2, "Data should be deduplicated by timestamp")

    def test_range_loading(self):
        candles = [{"timestamp": 1000, "close": 10}, {"timestamp": 2000, "close": 20}, {"timestamp": 3000, "close": 30}]
        self.storage.save_candles(self.symbol, self.interval, candles)

        df = self.storage.load_candles(self.symbol, self.interval, start_ts=1500, end_ts=2500)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["timestamp"], 2000)

    def test_last_timestamp(self):
        self.assertIsNone(self.storage.get_last_timestamp(self.symbol, self.interval))

        candles = [{"timestamp": 5000, "close": 50}]
        self.storage.save_candles(self.symbol, self.interval, candles)
        self.assertEqual(self.storage.get_last_timestamp(self.symbol, self.interval), 5000)


if __name__ == "__main__":
    unittest.main()
