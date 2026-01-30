import json

import pandas as pd

from scripts.maintenance.track_portfolio_state import accept_state, track_drift


def test_accept_state_lifecycle(tmp_path, monkeypatch):
    """Verify that accept_state correctly snapshots current optimal."""
    test_state_file = tmp_path / "portfolio_actual_state.json"
    monkeypatch.setattr("scripts.maintenance.track_portfolio_state.STATE_FILE", str(test_state_file))

    optimized_data = {"profiles": {"max_sharpe": {"assets": [{"Symbol": "X", "Weight": 1.0}]}}}
    monkeypatch.setattr("scripts.maintenance.track_portfolio_state._load_optimized_data", lambda: optimized_data)

    # Run accept
    accept_state(backup=False)

    assert test_state_file.exists()
    with open(test_state_file, "r") as f:
        saved = json.load(f)
        assert saved["max_sharpe"]["assets"][0]["Symbol"] == "X"


from tradingview_scraper.settings import get_settings


def test_partial_rebalance_dust_filtering(tmp_path, monkeypatch, capsys):
    """Verify that small drifts are skipped when feat_partial_rebalance is ON."""
    # Setup temporary state file
    test_state_file = tmp_path / "portfolio_actual_state.json"
    monkeypatch.setattr("scripts.maintenance.track_portfolio_state.STATE_FILE", str(test_state_file))

    # Enable feature flag
    settings = get_settings()
    settings.features.feat_partial_rebalance = True

    # 1. Create a "last implemented" state
    last_state = {"min_variance": {"assets": [{"Symbol": "A", "Weight": 0.50}, {"Symbol": "B", "Weight": 0.50}]}}
    with open(test_state_file, "w") as f:
        json.dump(last_state, f)

    # 2. Mock the "optimized_data" (target)
    # Asset A has 0.5% drift (Dust)
    # Asset B has 5% drift (Significant)
    # Asset C is new (Significant)
    optimized_data = {
        "profiles": {
            "min_variance": {
                "assets": [
                    {"Symbol": "A", "Weight": 0.505, "Market": "M1", "Description": "D1"},  # 0.5% drift
                    {"Symbol": "B", "Weight": 0.45, "Market": "M1", "Description": "D2"},  # -5% drift
                    {"Symbol": "C", "Weight": 0.045, "Market": "M1", "Description": "D3"},  # +4.5% drift
                ]
            }
        }
    }

    def mock_load_optimized():
        return optimized_data

    monkeypatch.setattr("scripts.maintenance.track_portfolio_state._load_optimized_data", mock_load_optimized)

    # Run track_drift with 1% threshold
    orders_csv = tmp_path / "orders.csv"
    track_drift(min_trade_threshold=0.01, orders_output=str(orders_csv))

    # Check output
    captured = capsys.readouterr()
    assert "SKIP (Dust)" in captured.out
    assert "EXECUTE" in captured.out

    # Verify orders CSV
    assert orders_csv.exists()
    orders_df = pd.read_csv(orders_csv)

    # Asset A should NOT be in orders (0.5% < 1%)
    assert "A" not in orders_df["Symbol"].values
    # Assets B and C SHOULD be in orders
    assert "B" in orders_df["Symbol"].values
    assert "C" in orders_df["Symbol"].values

    # Reset flag
    settings.features.feat_partial_rebalance = False
