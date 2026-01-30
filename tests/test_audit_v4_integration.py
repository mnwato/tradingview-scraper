import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# Ensure imports work for local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.backtest_engine import BacktestEngine
from tradingview_scraper.selection_engines.base import SelectionResponse


class TestAuditV4Integration(unittest.TestCase):
    def setUp(self):
        # Mock returns data
        self.dates = pd.date_range("2023-01-01", periods=100)
        self.returns = pd.DataFrame(np.random.normal(0, 0.01, (100, 3)), index=self.dates, columns=["BTC", "ETH", "SOL"])

    @patch("scripts.backtest_engine.AuditLedger")
    @patch("scripts.backtest_engine.build_selection_engine")
    @patch("scripts.backtest_engine.MarketRegimeDetector")
    @patch("scripts.backtest_engine.StrategySynthesizer")
    @patch("tradingview_scraper.settings.get_settings")
    def test_v4_telemetry_segregation(self, mock_settings, mock_synth, mock_regime, mock_build_engine, MockLedger):
        # 1. Setup Mock Settings & Ledger
        settings = MagicMock()
        settings.features.feat_audit_ledger = True
        settings.features.selection_mode = "v4"
        settings.benchmark_symbols = []
        settings.train_window = 60
        settings.test_window = 20
        settings.step_size = 20
        settings.prepare_summaries_run_dir.return_value = "/tmp"
        mock_settings.return_value = settings

        mock_ledger_instance = MockLedger.return_value

        # 2. Setup Mock Regime Detector
        mock_regime.return_value.detect_regime.return_value = ("NORMAL", {})

        # 3. Setup Mock Selection Engine (V4)

        mock_v4 = MagicMock()
        mock_v4.name = "v4_pipeline"

        # Simulate V4 Response with pipeline_audit
        dummy_audit = [{"stage": "Ingestion", "event": "DataLoaded"}, {"stage": "Inference", "event": "ScoringComplete"}]

        mock_selection_resp = SelectionResponse(
            winners=[{"symbol": "BTC", "direction": "LONG"}],
            audit_clusters={1: ["BTC", "ETH"]},
            spec_version="4.0-mlops",
            metrics={"alpha_mean": 0.5, "pipeline_audit": dummy_audit},
            relaxation_stage=1,
        )
        mock_v4.select.return_value = mock_selection_resp
        mock_build_engine.return_value = mock_v4

        # 3. Initialize Engine & Run Tournament (Single Window)
        # We mock load_data to avoid file dependency
        with patch.object(BacktestEngine, "load_data"):
            engine = BacktestEngine()
            engine.returns = self.returns
            engine.metadata = {"BTC": {"symbol": "BTC"}, "ETH": {"symbol": "ETH"}, "SOL": {"symbol": "SOL"}}

            # Run tournament for a small slice
            engine.run_tournament(train_window=60, test_window=20, step_size=100)

        # 4. Assertions on Ledger Recording
        # Check if record_outcome was called for 'backtest_select'
        select_calls = [call for call in mock_ledger_instance.record_outcome.call_args_list if call.kwargs.get("step") == "backtest_select"]

        self.assertTrue(len(select_calls) > 0, "record_outcome was not called for backtest_select")

        last_call = select_calls[0]
        metrics = last_call.kwargs.get("metrics")
        data = last_call.kwargs.get("data")

        # CR-420 Verification
        self.assertIn("alpha_mean", metrics)
        self.assertNotIn("pipeline_audit", metrics, "pipeline_audit should be removed from metrics")
        self.assertIn("pipeline_audit", data, "pipeline_audit should be moved to data")
        self.assertEqual(data["pipeline_audit"], dummy_audit)
        self.assertEqual(data["relaxation_stage"], 1)


if __name__ == "__main__":
    unittest.main()
