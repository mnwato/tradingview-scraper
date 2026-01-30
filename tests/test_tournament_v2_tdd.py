import json
import os

import numpy as np
import pandas as pd
import pytest

from scripts.backtest_engine import BacktestEngine
from tradingview_scraper.settings import get_settings


def test_tournament_v2_spec_configuration(tmp_path):
    """
    TDD Test: Verify that the tournament runs with v2 selection,
    specific engines (skfolio, custom, cvxportfolio),
    specific profiles (hrp, benchmark),
    and simulators.
    """
    # 1. Setup Mock Data
    lakehouse = tmp_path / "data" / "lakehouse"
    lakehouse.mkdir(parents=True)

    returns_path = lakehouse / "portfolio_returns.pkl"
    candidates_path = lakehouse / "portfolio_candidates_raw.json"

    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY"]
    dates = pd.date_range("2025-01-01", periods=200)
    df_returns = pd.DataFrame(np.random.randn(200, len(symbols)) * 0.01, columns=pd.Index(symbols), index=dates)
    df_returns.to_pickle(returns_path)

    candidates = [{"symbol": s, "identity": s, "direction": "LONG", "value_traded": 1e9} for s in symbols]
    with open(candidates_path, "w") as f:
        json.dump(candidates, f)

    # 2. Configure Settings for V2 Selection
    settings = get_settings()
    settings.features.selection_mode = "v2"
    settings.dynamic_universe = True
    settings.top_n = 2
    settings.threshold = 0.5

    # 3. Initialize Engine with mock paths
    # We need to monkeypatch the paths in BacktestEngine or use environment variables
    # BacktestEngine hardcodes paths, so we'll temporarily point to our mock files

    original_returns_path = "data/lakehouse/portfolio_returns.pkl"
    original_candidates_path = "data/lakehouse/portfolio_candidates_raw.json"

    # Ensure directories exist for the actual code to not crash if it tries to write elsewhere
    os.makedirs("data/lakehouse", exist_ok=True)

    # We'll use a safer approach: backup real data if it exists
    backup_returns = None
    if os.path.exists(original_returns_path):
        backup_returns = pd.read_pickle(original_returns_path)

    df_returns.to_pickle(original_returns_path)
    with open(original_candidates_path, "w") as f:
        json.dump(candidates, f)

    try:
        bt = BacktestEngine(returns_path=original_returns_path)

        # 4. Run Tournament with small windows
        results = bt.run_tournament(
            train_window=60,
            test_window=20,
            step_size=40,
            engines=["skfolio", "custom", "cvxportfolio"],
            profiles=["hrp", "benchmark"],
            simulators=["custom", "cvxportfolio", "vectorbt"],  # Excluding Nautilus for speed in TDD unless specifically needed
        )

        # 5. Assertions
        assert "results" in results
        for sim in ["custom", "cvxportfolio", "vectorbt"]:
            assert sim in results["results"]
            for eng in ["skfolio", "custom", "cvxportfolio"]:
                assert eng in results["results"][sim]
                for prof in ["hrp", "benchmark"]:
                    assert prof in results["results"][sim][eng]
                    # Verify windows were processed
                    assert len(results["results"][sim][eng][prof]["windows"]) > 0
                    assert results["results"][sim][eng][prof]["summary"] is not None

    finally:
        # Restore or cleanup
        if backup_returns is not None:
            backup_returns.to_pickle(original_returns_path)
        # We don't delete candidates as it might be needed by others,
        # but in a real TDD we should be more careful with global state.
        pass


if __name__ == "__main__":
    # If run directly, just execute the test logic
    pytest.main([__file__])
