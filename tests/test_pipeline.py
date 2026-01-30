import os
import shutil
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd

from tradingview_scraper.pipeline import QuantitativePipeline


class TestQuantitativePipeline(unittest.TestCase):
    def setUp(self):
        self.base_path = ".gemini/tmp/test_pipeline_lakehouse"
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path)
        self.pipeline = QuantitativePipeline(lakehouse_path=self.base_path)

    @patch("tradingview_scraper.pipeline.AsyncScreener.screen_many", new_callable=AsyncMock)
    @patch("tradingview_scraper.pipeline.FuturesUniverseSelector")
    @patch("tradingview_scraper.pipeline.load_config")
    def test_run_discovery_async(self, mock_load_config, mock_selector_cls, mock_screen_many):
        # Setup mock config
        mock_load_config.return_value = MagicMock()

        # Setup mock selector for dry_run
        mock_selector = MagicMock()
        mock_selector.run.return_value = {"payloads": [{"market": "crypto"}]}
        mock_selector.process_data.return_value = {"status": "success", "data": [{"symbol": "BINANCE:BTCUSDT"}]}
        mock_selector_cls.return_value = mock_selector

        # Setup mock results from AsyncScreener
        mock_screen_many.return_value = [{"status": "success", "data": [{"symbol": "BTC_RAW"}]}]

        configs = ["configs/crypto_cex_trend_binance_spot_daily_long.yaml"]
        signals = self.pipeline.run_discovery(configs)

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["symbol"], "BINANCE:BTCUSDT")
        self.assertEqual(signals[0]["direction"], "LONG")

        # Verify dry_run was used
        mock_selector.run.assert_called_with(dry_run=True)
        # Verify process_data was used with results from screen_many
        mock_selector.process_data.assert_called()

    @patch("tradingview_scraper.pipeline.QuantitativePipeline.run_discovery")
    @patch("tradingview_scraper.pipeline.PersistentDataLoader")
    @patch("tradingview_scraper.pipeline.BarbellOptimizer")
    @patch("tradingview_scraper.pipeline.MarketRegimeDetector")
    @patch("tradingview_scraper.pipeline.AntifragilityAuditor")
    def test_run_full_pipeline_success(self, mock_audit, mock_regime, mock_opt, mock_loader, mock_discovery):
        mock_discovery.return_value = [{"symbol": "BINANCE:BTCUSDT", "direction": "LONG"}]

        # Mock Loader
        dates = pd.date_range("2025-01-01", periods=10)
        df = pd.DataFrame({"timestamp": dates.view("int64") // 10**9, "close": np.linspace(100, 110, 10)})
        mock_loader.return_value.load.return_value = df

        # Mock Optimizer output
        mock_opt.return_value.optimize.return_value = pd.DataFrame([{"Symbol": "BINANCE:BTCUSDT", "Weight": 1.0, "Type": "CORE (Safe)"}])

        result = self.pipeline.run_full_pipeline(["configs/test.yaml"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_signals"], 1)

    @patch("tradingview_scraper.pipeline.QuantitativePipeline.run_discovery")
    def test_run_full_pipeline_no_signals(self, mock_discovery):
        mock_discovery.return_value = []

        result = self.pipeline.run_full_pipeline(["configs/test.yaml"])
        self.assertEqual(result["status"], "no_signals")

    @patch("tradingview_scraper.pipeline.QuantitativePipeline.run_discovery")
    @patch("tradingview_scraper.pipeline.PersistentDataLoader")
    @patch("tradingview_scraper.pipeline.BarbellOptimizer")
    @patch("tradingview_scraper.pipeline.MarketRegimeDetector")
    @patch("tradingview_scraper.pipeline.AntifragilityAuditor")
    def test_run_full_pipeline_integrated(self, mock_audit, mock_regime, mock_opt_cls, mock_loader_cls, mock_discovery):
        # 1. Mock Discovery
        mock_discovery.return_value = [
            {"symbol": "BINANCE:BTCUSDT", "direction": "LONG", "ADX": 30, "Value.Traded": 1e8},
            {"symbol": "BINANCE:ETHUSDT", "direction": "LONG", "ADX": 25, "Value.Traded": 5e7},
        ]

        # 2. Mock Data Loader (Return dummy historical data)
        mock_loader = mock_loader_cls.return_value
        dates = pd.date_range("2025-01-01", periods=10)
        df = pd.DataFrame({"timestamp": dates.view("int64") // 10**9, "close": np.linspace(100, 110, 10)})
        mock_loader.load.return_value = df

        # 3. Mock Regime and Optimizer
        mock_regime.return_value.detect_regime.return_value = "NORMAL"
        mock_opt = mock_opt_cls.return_value
        mock_opt.optimize.return_value = pd.DataFrame([{"Symbol": "BINANCE:BTCUSDT", "Weight": 0.5, "Type": "CORE (Safe)"}, {"Symbol": "BINANCE:ETHUSDT", "Weight": 0.5, "Type": "CORE (Safe)"}])

        result = self.pipeline.run_full_pipeline(["configs/test.yaml"])

        self.assertEqual(result["status"], "success")
        self.assertIn("portfolio", result)
        self.assertEqual(len(result["portfolio"]), 2)

    def tearDown(self):
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path)


if __name__ == "__main__":
    unittest.main()
