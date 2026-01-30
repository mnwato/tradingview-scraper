import numpy as np
import pandas as pd

from scripts.natural_selection import run_selection
from tradingview_scraper.settings import get_settings


def test_mps_veto_logic():
    """MPS 3.0 should veto assets with near-zero probability in any category."""
    symbols = ["STABLE", "FRAGILE"]
    # Make them highly correlated but not identical
    data = np.random.randn(200, 1) * 0.01
    returns = pd.DataFrame({"STABLE": data.flatten() + np.random.randn(200) * 0.0001, "FRAGILE": data.flatten() + np.random.randn(200) * 0.0001}, index=pd.date_range("2023-01-01", periods=200))

    # Give both high alpha to pass ECI
    returns += 0.05

    raw_candidates = [
        {"symbol": "STABLE", "identity": "STABLE", "direction": "LONG", "value_traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "FRAGILE", "identity": "FRAGILE", "direction": "LONG", "value_traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
    ]

    # FRAGILE has very low survival score
    stats_df = pd.DataFrame({"Symbol": symbols, "Antifragility_Score": [0.5, 0.5], "Fragility_Score": [0.1, 0.1], "Regime_Survival_Score": [1.0, 0.01]}).set_index("Symbol")

    settings = get_settings()
    settings.features.feat_dynamic_selection = False

    response = run_selection(returns, raw_candidates, stats_df, top_n=1, threshold=0.5, mode="v3")

    selected = [w["symbol"] for w in response.winners]
    assert "STABLE" in selected
    assert "FRAGILE" not in selected


def test_v3_metadata_veto():
    """Ensure assets without required metadata are vetoed in v3."""
    symbols = ["COMPLETE", "INCOMPLETE"]
    data = np.random.randn(200, 1) * 0.01
    returns = pd.DataFrame({"COMPLETE": data.flatten(), "INCOMPLETE": data.flatten()}, index=pd.date_range("2023-01-01", periods=200))
    # Give both high alpha to pass ECI
    returns += 0.05

    raw_candidates = [
        {"symbol": "COMPLETE", "identity": "COMPLETE", "direction": "LONG", "value_traded": 1e10, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "INCOMPLETE", "identity": "INCOMPLETE", "direction": "LONG", "value_traded": 1e10},  # Missing metadata
    ]

    settings = get_settings()
    settings.features.feat_dynamic_selection = False

    response = run_selection(returns, raw_candidates, None, top_n=1, threshold=0.5, mode="v3")

    selected = [w["symbol"] for w in response.winners]
    assert "COMPLETE" in selected
    assert "INCOMPLETE" not in selected


def test_v3_eci_veto():
    """Ensure assets with high implementation cost (low liquidity) are vetoed in v3."""
    symbols = ["LIQUID", "ILLIQUID"]
    data = np.random.randn(200, 1) * 0.01
    returns = pd.DataFrame({"LIQUID": data.flatten(), "ILLIQUID": data.flatten()}, index=pd.date_range("2023-01-01", periods=200))
    # Give them both high alpha so they are candidates
    returns += 0.05

    raw_candidates = [
        {"symbol": "LIQUID", "identity": "LIQUID", "direction": "LONG", "value_traded": 1e10, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "ILLIQUID", "identity": "ILLIQUID", "direction": "LONG", "value_traded": 1e2, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
    ]

    settings = get_settings()
    settings.features.feat_dynamic_selection = False

    response = run_selection(returns, raw_candidates, None, top_n=1, threshold=0.5, mode="v3")

    selected = [w["symbol"] for w in response.winners]
    assert "LIQUID" in selected
    assert "ILLIQUID" not in selected


def test_v3_aggressive_pruning_kappa():
    """Ensure top_n is forced to 1 if kappa is high."""
    symbols = ["S1", "S2"]
    # Make them almost identical to force high kappa
    data = np.random.randn(200, 1) * 0.01
    returns = pd.DataFrame(
        {
            "S1": data.flatten(),
            "S2": data.flatten() + 1e-10,  # Tiny difference
        },
        index=pd.date_range("2023-01-01", periods=200),
    )
    # High alpha to pass ECI
    returns += 0.05

    raw_candidates = [
        {"symbol": "S1", "identity": "S1", "direction": "LONG", "value_traded": 1e10, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "S2", "identity": "S2", "direction": "LONG", "value_traded": 1e10, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
    ]

    settings = get_settings()
    settings.features.feat_dynamic_selection = False

    # Request 2 winners per cluster
    response = run_selection(returns, raw_candidates, None, top_n=2, threshold=0.5, mode="v3")

    # Because kappa is high, it should have been forced to 1 winner per cluster
    assert len(response.winners) == 1
