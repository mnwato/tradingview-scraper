import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from tradingview_scraper.pipelines.discovery.tradingview import TradingViewDiscoveryScanner
from tradingview_scraper.pipelines.discovery.base import CandidateMetadata


class TestScannerHardening(unittest.TestCase):
    def setUp(self):
        self.scanner = TradingViewDiscoveryScanner()

    @patch("tradingview_scraper.pipelines.discovery.tradingview.load_config")
    @patch("tradingview_scraper.futures_universe_selector.FuturesUniverseSelector.run")
    @patch("tradingview_scraper.pipelines.selection.base.FoundationHealthRegistry.is_healthy")
    def test_scanner_vetoes_toxic_assets(self, mock_healthy, mock_selector_run, mock_load_config):
        """Verify that scanners correctly apply Registry-Aware Vetoes."""
        # Mock config
        mock_load_config.return_value = MagicMock()

        # Setup mock selector output
        mock_selector_run.return_value = {"status": "success", "data": [{"symbol": "BINANCE:BTCUSDT", "volume": 1000, "close": 50000}, {"symbol": "BINANCE:TOXIC", "volume": 999999, "close": 1}]}

        # Mock health: BTC is healthy, TOXIC is NOT.
        def health_check(sym):
            return sym == "BINANCE:BTCUSDT"

        mock_healthy.side_effect = health_check
        self.scanner.registry.data = {"BINANCE:TOXIC": {"status": "toxic"}}

        # Run discovery
        cands = self.scanner.discover({"config_path": "test.yaml"})

        # Verify veto
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].symbol, "BINANCE:BTCUSDT")

    def test_path_determinism(self):
        """Verify that scanner configs use settings for path resolution."""
        from tradingview_scraper.settings import get_settings

        settings = get_settings()
        self.assertIsNotNone(settings.configs_dir)


if __name__ == "__main__":
    unittest.main()
