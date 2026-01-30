import numpy as np
import pandas as pd

from scripts.natural_selection import run_selection
from tradingview_scraper.settings import get_settings


def test_v2_selection_basic():
    """Verify CARS 2.0 (v2) selection logic."""
    symbols = ["S1", "S2", "S3"]
    returns = pd.DataFrame(np.random.randn(200, 3) * 0.01, columns=pd.Index(symbols), index=pd.date_range("2023-01-01", periods=200))

    # S1 is clearly best
    returns["S1"] += 0.05

    raw_candidates = [
        {"symbol": "S1", "identity": "S1", "direction": "LONG", "value_traded": 1e9},
        {"symbol": "S2", "identity": "S2", "direction": "LONG", "value_traded": 1e9},
        {"symbol": "S3", "identity": "S3", "direction": "LONG", "value_traded": 1e9},
    ]

    # Explicitly use v2 mode
    response = run_selection(returns, raw_candidates, None, top_n=1, threshold=0.5, mode="v2")

    selected = [w["symbol"] for w in response.winners]
    assert "S1" in selected
    assert len(response.winners) > 0


def test_legacy_selection_logic():
    """Verify legacy local normalization logic."""
    symbols = ["S1", "S2"]
    data = np.random.randn(200, 2) * 0.01
    returns = pd.DataFrame(data, columns=pd.Index(symbols), index=pd.date_range("2023-01-01", periods=200))

    # S1 is better
    returns["S1"] += 0.05

    raw_candidates = [
        {"symbol": "S1", "identity": "S1", "direction": "LONG", "value_traded": 1e9},
        {"symbol": "S2", "identity": "S2", "direction": "LONG", "value_traded": 1e9},
    ]

    # Explicitly use legacy mode
    response = run_selection(returns, raw_candidates, None, top_n=1, threshold=0.5, mode="legacy")

    selected = [w["symbol"] for w in response.winners]
    assert "S1" in selected
    assert len(response.winners) > 0


def test_v2_dynamic_selection():
    """Verify dynamic selection logic in v2 mode."""
    # Highly correlated assets in one cluster
    symbols = ["S1", "S2", "S3", "S4"]
    data = np.random.randn(200, 1) * 0.01
    returns = pd.DataFrame({s: data.flatten() + np.random.randn(200) * 1e-6 for s in symbols}, index=pd.date_range("2023-01-01", periods=200))
    returns += 0.01

    raw_candidates = [{"symbol": s, "identity": s, "direction": "LONG", "value_traded": 1e9} for s in symbols]

    settings = get_settings()
    settings.features.feat_dynamic_selection = True

    # Request top_n=4, but high correlation should prune it down
    # Force 1 cluster with high threshold
    response = run_selection(returns, raw_candidates, None, top_n=4, threshold=10.0, mode="v2")

    # Correlation is near 1.0, so top_n * (1 - 1.0) + 0.5 rounded should be 1
    assert len(response.winners) == 1
