import json
import os
import sys
from typing import cast

import numpy as np
import pandas as pd
import pytest

# Ensure imports work for local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.backtest_engine import BacktestEngine  # type: ignore
from tradingview_scraper.portfolio_engines.base import EngineRequest, ProfileName
from tradingview_scraper.portfolio_engines import build_engine
from tradingview_scraper.settings import get_settings


@pytest.fixture
def sample_returns(tmp_path):
    """Create a synthetic returns matrix for testing."""
    # Seed for reproducibility
    rng = np.random.default_rng(42)
    dates = pd.date_range("2023-01-01", periods=100, tz="UTC")
    # Using a slightly negative mean to ensure some negative values for CVaR
    df = pd.DataFrame(rng.normal(-0.001, 0.02, (100, 5)), index=dates, columns=["A", "B", "C", "D", "E"])  # type: ignore
    # Force some volatility differences for PIT testing
    df["E"] = df["E"] * 5  # High risk asset

    path = tmp_path / "returns.pkl"
    df.to_pickle(path)
    return path


def test_pit_risk_auditing(sample_returns):
    """Verify that backtest stats change when PIT fidelity is enabled."""
    bt = BacktestEngine(returns_path=str(sample_returns))
    settings = get_settings()

    # 1. Flag OFF -> Should return static 0.5 scores
    settings.features.feat_pit_fidelity = False
    stats_legacy = bt._audit_training_stats(bt.returns.iloc[:50])
    assert (stats_legacy["Antifragility_Score"] == 0.5).all()

    # 2. Flag ON -> Should return dynamic scores from AntifragilityAuditor
    settings.features.feat_pit_fidelity = True
    stats_pit = bt._audit_training_stats(bt.returns.iloc[:50])

    # Check that scores are dynamic (not all 0.5)
    assert not (stats_pit["Antifragility_Score"] == 0.5).all()
    # Check that the high-risk asset E has a different score/vol than A
    assert stats_pit.set_index("Symbol").loc["E", "Vol"] > stats_pit.set_index("Symbol").loc["A", "Vol"]


def test_market_equal_weight_baseline(sample_returns):
    """Verify the new 'equal_weight' profile in the market engine."""
    bt = BacktestEngine(returns_path=str(sample_returns))
    engine = build_engine("market")

    # Setup request for EW
    req = EngineRequest(profile=cast(ProfileName, "equal_weight"))

    # Test with 5 assets
    resp = engine.optimize(returns=bt.returns, clusters={}, meta={}, stats=None, request=req)

    weights = resp.weights
    assert len(weights) == 5
    assert np.isclose(weights["Weight"].sum(), 1.0)
    assert (weights["Weight"] == 0.2).all()
    assert weights["Cluster_ID"].iloc[0] == "MARKET_EW"


def test_cross_window_state_persistence(sample_returns, monkeypatch):
    """Verify that holdings are propagated between windows in run_tournament."""
    # Mock _load_initial_state to return empty dict
    monkeypatch.setattr(BacktestEngine, "_load_initial_state", lambda self: {})

    bt = BacktestEngine(returns_path=str(sample_returns))

    settings = get_settings()
    settings.features.feat_pit_fidelity = False  # Speed up

    # We want to check if prev_weights is passed to _compute_weights correctly
    # and if the simulator's final holdings are stored.

    recorded_prev_weights = []

    original_compute = bt._compute_weights

    def mock_compute(*args, **kwargs):
        # prev_weights is 8th positional arg or keyword 'prev_weights'
        p_w = kwargs.get("prev_weights")
        if p_w is None and len(args) >= 8:
            p_w = args[7]
        recorded_prev_weights.append(p_w)
        return original_compute(*args, **kwargs)

    monkeypatch.setattr(bt, "_compute_weights", mock_compute)

    # Run a small 2-window tournament
    bt.run_tournament(train_window=40, test_window=20, step_size=20, engines=["custom"], profiles=["min_variance"], simulators=["custom"])

    # Window 1: prev_weights should be empty/None
    assert recorded_prev_weights[0] is None or recorded_prev_weights[0].empty

    # Window 2: prev_weights should contain weights from Window 1
    assert recorded_prev_weights[1] is not None
    assert not recorded_prev_weights[1].empty
    assert "A" in recorded_prev_weights[1].index


def test_backtest_audit_trail(sample_returns, tmp_path):
    """Verify that backtest windows contribute to the audit ledger."""
    settings = get_settings()
    settings.features.feat_audit_ledger = True

    # Redirect summaries to tmp_path
    settings.summaries_dir = tmp_path

    bt = BacktestEngine(returns_path=str(sample_returns))

    # Run tournament
    bt.run_tournament(train_window=40, test_window=20, step_size=20, engines=["custom"], profiles=["min_variance"], simulators=["custom"])

    # Check for audit.jsonl in the run directory
    run_dir = settings.summaries_run_dir
    audit_file = run_dir / "audit.jsonl"
    assert audit_file.exists()

    with open(audit_file, "r") as f:
        lines = f.readlines()

    # Should have backtest_optimize entries
    optimize_entries = [json.loads(l) for l in lines if json.loads(l).get("step") == "backtest_optimize"]
    assert len(optimize_entries) >= 2  # 2 windows * (intent + outcome)

    # Check intent has train_returns hash
    intent = next(e for e in optimize_entries if e["status"] == "intent")
    assert "train_returns" in intent["intent"]["input_hashes"]

    # Check outcome has window_weights hash
    outcome = next(e for e in optimize_entries if e["status"] == "success")
    assert "window_weights" in outcome["outcome"]["output_hashes"]
