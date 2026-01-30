import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# We import the module to be tested (which doesn't exist yet)
# so we expect this to fail initially if run, but for TDD we write the test first.
# We will create the file in the next step.
from scripts.services.backfill_features import BackfillService


@pytest.fixture
def mock_workspace(tmp_path):
    """Creates a mock workspace with candidates and lakehouse data."""
    # Setup directories
    lakehouse_dir = tmp_path / "data" / "lakehouse"
    lakehouse_dir.mkdir(parents=True)

    # Create dummy OHLCV data for 2 symbols
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")

    # Symbol A: Uptrend (Should have high rating)
    price_a = np.linspace(100, 200, 100)
    df_a = pd.DataFrame({"open": price_a, "high": price_a + 1, "low": price_a - 1, "close": price_a, "volume": 1000}, index=dates)
    df_a.to_parquet(lakehouse_dir / "SYMBOL_A_1d.parquet")

    # Symbol B: Downtrend (Should have low rating)
    price_b = np.linspace(200, 100, 100)
    df_b = pd.DataFrame({"open": price_b, "high": price_b + 1, "low": price_b - 1, "close": price_b, "volume": 1000}, index=dates)
    df_b.to_parquet(lakehouse_dir / "SYMBOL_B_1d.parquet")

    # Create candidates.json
    candidates = [{"symbol": "SYMBOL:A", "description": "Test A"}, {"symbol": "SYMBOL:B", "description": "Test B"}]
    candidates_path = tmp_path / "candidates.json"
    with open(candidates_path, "w") as f:
        json.dump(candidates, f)

    return {"root": tmp_path, "lakehouse": lakehouse_dir, "candidates": candidates_path, "output": tmp_path / "features_matrix.parquet"}


def test_backfill_execution(mock_workspace):
    """Test that the backfill service generates the output matrix."""
    service = BackfillService(lakehouse_dir=mock_workspace["lakehouse"])

    service.run(candidates_path=mock_workspace["candidates"], output_path=mock_workspace["output"])

    assert mock_workspace["output"].exists()

    df = pd.read_parquet(mock_workspace["output"])
    assert not df.empty
    # Columns are MultiIndex (symbol, feature)
    # Check if symbol level exists
    assert "SYMBOL:A" in df.columns.get_level_values(0)
    assert "SYMBOL:B" in df.columns.get_level_values(0)

    # Verify rating logic direction
    # Symbol A (Uptrend) should have positive rating at the end
    # We access the specific feature 'recommend_all'
    assert df[("SYMBOL:A", "recommend_all")].iloc[-1] > 0

    # Symbol B (Downtrend) should have negative rating at the end
    assert df[("SYMBOL:B", "recommend_all")].iloc[-1] < 0

    # Verify range
    assert df.max().max() <= 1.0
    assert df.min().min() >= -1.0
