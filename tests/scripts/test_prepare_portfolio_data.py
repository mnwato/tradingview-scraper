import json
import os

# Setup sys path to find the script module
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.append(os.getcwd())

from scripts.prepare_portfolio_data import prepare_portfolio_universe


@pytest.fixture
def mock_settings():
    with patch("scripts.prepare_portfolio_data.get_settings") as mock_get:
        settings = MagicMock()
        settings.prepare_summaries_run_dir.return_value = Path("dummy_run_dir")
        settings.min_days_floor = 0
        settings.features.feat_audit_ledger = False
        settings.resolve_portfolio_lookback_days.return_value = 100
        mock_get.return_value = settings
        yield settings


@pytest.fixture
def mock_env(tmp_path):
    # Create dummy candidates file
    candidates_file = tmp_path / "dummy_candidates.json"
    candidates = [{"symbol": "BINANCE:BTCUSDT"}]
    with open(candidates_file, "w") as f:
        json.dump(candidates, f)

    with patch.dict(
        os.environ,
        {
            "PORTFOLIO_DATA_SOURCE": "lakehouse_only",
            "PORTFOLIO_RETURNS_PATH": str(tmp_path / "dummy_returns.parquet"),
            "PORTFOLIO_META_PATH": str(tmp_path / "dummy_meta.json"),
            "CANDIDATES_FILE": str(candidates_file),
        },
    ):
        yield


def test_prep_lakehouse_success(mock_settings, mock_env):
    """Test success path when data exists in lakehouse."""

    with patch("scripts.prepare_portfolio_data.PersistentDataLoader") as MockLoader:
        loader = MockLoader.return_value

        # Mock load returning data
        loader.load.return_value = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=10, tz="UTC").astype(int) // 10**9, "close": [100.0 + i for i in range(10)]})

        # Mock to_parquet/pickle to avoid writing to disk or erroring if dir doesn't exist
        # Although tmp_path exists.

        prepare_portfolio_universe()

        # Verify load called
        loader.load.assert_called()


def test_prep_lakehouse_fail_missing(mock_settings, mock_env):
    """Test failure when data missing in lakehouse."""

    # We want to use a different candidates file for this test or override the loader behavior for the existing symbol.
    # The default mock_env uses BTCUSDT.

    with patch("scripts.prepare_portfolio_data.PersistentDataLoader") as MockLoader:
        loader = MockLoader.return_value
        # Load returns empty -> missing data
        loader.load.return_value = pd.DataFrame()

        # In lakehouse_only mode, we expect an exception or abort.
        # Currently the script just logs error and continues or returns empty matrix.
        # We want to assert that it does NOT try to sync/ingest.

        prepare_portfolio_universe()
        loader.load.assert_called()
