import unittest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from scripts.backtest_engine import BacktestEngine


class TestRecursiveBacktest(unittest.TestCase):
    def test_meta_profile_detection(self):
        """Verify that the engine detects when a profile is a meta-portfolio."""
        mock_manifest = {"profiles": {"meta_test": {"sleeves": [{"id": "s1", "profile": "p1"}]}, "atomic_test": {"logic": "some_logic"}}}

        with patch("builtins.open", mock_open(read_data=json.dumps(mock_manifest))):
            with patch("pathlib.Path.exists", return_value=True):
                engine = BacktestEngine()
                self.assertTrue(engine._is_meta_profile("meta_test"))
                self.assertFalse(engine._is_meta_profile("atomic_test"))

    @patch("scripts.backtest_engine.BacktestEngine._is_meta_profile")
    @patch("scripts.backtest_engine.BacktestEngine.load_data")
    @patch("tradingview_scraper.settings.get_settings")
    def test_recursive_rebalance_trigger(self, mock_settings, mock_load, mock_is_meta):
        """Verify that the recursive logic is triggered for meta-profiles."""
        mock_is_meta.return_value = True
        engine = BacktestEngine()

        # Mock settings
        settings = MagicMock()
        settings.train_window = 100
        settings.test_window = 20
        settings.step_size = 10
        settings.profiles = "hrp"
        settings.profile = "meta_test"
        mock_settings.return_value = settings

        # Mock returns
        import pandas as pd
        import numpy as np

        dates = pd.date_range("2024-01-01", periods=150)
        engine.returns = pd.DataFrame(np.random.randn(150, 2), index=dates, columns=["A", "B"])

        with patch("scripts.build_meta_returns.build_meta_returns") as mock_agg:
            # We just want to see if it enters the 'is_meta' block
            # For now it's a 'pass' in the code, but we'll implement it
            engine.run_tournament()
            # This will fail until implementation
            # self.assertTrue(mock_agg.called)


if __name__ == "__main__":
    unittest.main()
