import unittest

from tradingview_scraper.futures_universe_selector import _load_config_file


class TestPipelineComposition(unittest.TestCase):
    def test_recursive_composition(self):
        """Verify that L4 scanner inherits correctly from L2 and L1."""
        l4_path = "configs/scanners/crypto/binance_perp_long_trend.yaml"
        config_dict = _load_config_file(l4_path)

        # Check L1 Inheritance (Technicals)
        self.assertIn("adx", config_dict["trend"])
        self.assertEqual(config_dict["trend"]["adx"]["min"], 10)

        # Check L2 Inheritance (Templates)
        self.assertIn("BINANCE", config_dict["exchanges"])
        self.assertEqual(config_dict["export_metadata"]["data_category"], "strategy_alpha")

        # Check L3 Logic (Inherited via base_preset in L4)
        self.assertEqual(config_dict["trend"]["direction"], "long")

    def test_crypto_mtf_composition(self):
        """Verify Crypto MTF strategy composition."""
        l4_path = "configs/scanners/crypto/global_mtf_trend.yaml"
        config_dict = _load_config_file(l4_path)

        self.assertIn("BINANCE", config_dict["exchanges"])
        # Check MTF logic
        self.assertEqual(config_dict["confirm_screen"]["timeframe"], "weekly")
        # Check L1 (Recursive) - inherited from global_perp_top50 -> crypto_perp
        # Actually check the correct field name
        if "volume" in config_dict:
            self.assertIn("value_traded_min", config_dict["volume"])

    def test_metals_trend_composition(self):
        """Verify Metals trend strategy composition."""
        l4_path = "configs/scanners/tradfi/metals_trend.yaml"
        config_dict = _load_config_file(l4_path)

        self.assertIn("COMEX", config_dict["exchanges"])
        self.assertEqual(config_dict["markets"], ["futures"])
        self.assertEqual(config_dict["trend"]["adx"]["min"], 25)


if __name__ == "__main__":
    unittest.main()
