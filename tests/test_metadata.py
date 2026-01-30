import os
import shutil
import unittest

import pandas as pd

from tradingview_scraper.symbols.stream.metadata import MetadataCatalog


class TestMetadataCatalog(unittest.TestCase):
    def setUp(self):
        # Use a temp path for testing
        self.base_path = ".gemini/tmp/test_lakehouse"
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path)
        self.catalog = MetadataCatalog(base_path=self.base_path)

    def test_upsert_and_get(self):
        symbols = [
            {"symbol": "BINANCE:BTCUSDT", "exchange": "BINANCE", "base": "BTC", "quote": "USDT", "type": "spot", "pricescale": 100, "minmov": 1, "active": True},
            {"symbol": "BINANCE:ETHUSDT", "exchange": "BINANCE", "base": "ETH", "quote": "USDT", "active": False},
        ]

        self.catalog.upsert_symbols(symbols)

        # Verify BTC
        btc = self.catalog.get_instrument("BINANCE:BTCUSDT")
        self.assertIsNotNone(btc)
        self.assertEqual(btc["base"], "BTC")
        self.assertEqual(btc["pricescale"], 100)

        # Verify Active list
        active = self.catalog.list_active_symbols(exchange="BINANCE")
        self.assertIn("BINANCE:BTCUSDT", active)
        # Note: list_active_symbols logic might need update if it depends on 'active' flag explicitly
        # or if it implies 'currently valid record'.
        # The current implementation checks [active==True].
        self.assertNotIn("BINANCE:ETHUSDT", active)

    def test_pit_versioning(self):
        import time

        # 1. Initial Insert
        symbol_data = [{"symbol": "BINANCE:BTCUSDT", "pricescale": 100, "active": True}]
        self.catalog.upsert_symbols(symbol_data)

        # Capture time after first insert
        t1 = pd.Timestamp.now()
        time.sleep(1.0)  # Ensure minimal time gap

        # 2. Update (Change pricescale)
        symbol_data[0]["pricescale"] = 1000
        self.catalog.upsert_symbols(symbol_data)

        # 3. Verify Current (Latest)
        current = self.catalog.get_instrument("BINANCE:BTCUSDT")
        self.assertEqual(current["pricescale"], 1000)

        # 4. Verify History (at t1)
        # Lookup at t1 should return the record valid at that time
        past = self.catalog.get_instrument("BINANCE:BTCUSDT", as_of=t1)
        self.assertIsNotNone(past)
        self.assertEqual(past["pricescale"], 100)

    def test_delisting_flow(self):
        import time

        # 1. Active
        symbol = "BINANCE:DELISTED"
        self.catalog.upsert_symbols([{"symbol": symbol, "active": True}])
        t_active = pd.Timestamp.now()

        # 2. Retire
        time.sleep(0.1)
        self.catalog.retire_symbols([symbol])
        t_retired = pd.Timestamp.now()

        # 3. Verify Current (Latest state is Inactive)
        current = self.catalog.get_instrument(symbol)
        self.assertIsNotNone(current)
        self.assertFalse(current["active"])

        # 4. Verify PIT History (Record at t_active was Active)
        past = self.catalog.get_instrument(symbol, as_of=t_active)
        self.assertIsNotNone(past)
        self.assertEqual(past["symbol"], symbol)
        self.assertTrue(past["active"])

    def tearDown(self):
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path)
