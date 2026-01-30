import unittest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from tradingview_scraper.settings import get_settings


class TestPathDeterminism(unittest.TestCase):
    def test_settings_source_of_truth(self):
        """Verify that settings can be overridden by env vars correctly."""
        with patch.dict(os.environ, {"TV_LAKEHOUSE_DIR": "/tmp/custom_lakehouse"}):
            get_settings.cache_clear()
            settings = get_settings()
            self.assertEqual(str(settings.lakehouse_dir), "/tmp/custom_lakehouse")

    def test_alpha_readonly_default(self):
        """Verify prepare_portfolio_data defaults to lakehouse_only."""
        from scripts.prepare_portfolio_data import get_data_source

        # We need to simulate the environment
        with patch.dict(os.environ, {}, clear=True):
            source = get_data_source()
            self.assertEqual(source, "lakehouse_only")

    def test_meta_parity_path_resolution(self):
        """Verify validate_meta_parity uses settings for run dir."""
        from scripts.validate_meta_parity import _resolve_run_dir

        settings = get_settings()
        run_id = "test_run_123"
        expected = (settings.summaries_runs_dir / run_id).resolve()

        # Mocking existence to avoid actual FS calls
        with patch.object(Path, "exists", return_value=True):
            resolved = _resolve_run_dir(run_id).resolve()
            self.assertEqual(resolved, expected)


if __name__ == "__main__":
    unittest.main()
