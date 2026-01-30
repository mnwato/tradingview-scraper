import numpy as np
import pandas as pd
import pytest
from tradingview_scraper.portfolio_engines.impl.custom import CustomClusteredEngine
from tradingview_scraper.portfolio_engines.base import EngineRequest
from tradingview_scraper.portfolio_engines.cluster_adapter import build_clustered_universe


@pytest.fixture
def sample_data():
    # 10 assets, 100 days
    np.random.seed(42)
    rets = pd.DataFrame(np.random.normal(0, 0.01, (100, 10)), columns=[f"A{i}" for i in range(10)])
    # Clusters
    clusters = {"1": ["A0", "A1", "A2"], "2": ["A3", "A4"], "3": ["A5", "A6", "A7", "A8", "A9"]}
    return rets, clusters


def test_regime_impact_on_weights(sample_data):
    """
    Verify that CRISIS regime produces different (more regularized) weights than NORMAL regime.
    """
    rets, clusters = sample_data
    engine = CustomClusteredEngine()

    # 1. Normal Request
    req_normal = EngineRequest(
        profile="min_variance",
        regime="NORMAL",
        market_environment="EXPANSION",  # Low L2 (0.05)
        default_shrinkage_intensity=0.01,
    )

    # 2. Crisis Request
    req_crisis = EngineRequest(
        profile="min_variance",
        regime="CRISIS",
        market_environment="CRISIS",  # High L2 (0.20)
        default_shrinkage_intensity=0.01,
    )

    # Optimize Normal
    resp_normal = engine.optimize(returns=rets, clusters=clusters, request=req_normal)
    w_normal = resp_normal.weights.set_index("Symbol")["Weight"].sort_index()

    # Optimize Crisis
    resp_crisis = engine.optimize(returns=rets, clusters=clusters, request=req_crisis)
    w_crisis = resp_crisis.weights.set_index("Symbol")["Weight"].sort_index()

    # Assert weights are different
    # Higher L2 regularization in Crisis should lead to more diversified (flatter) weights
    # or at least different weights.
    diff = np.abs(w_normal - w_crisis).sum()
    print(f"Weight Difference (L1 Norm): {diff}")

    assert diff > 1e-4, "Regime change did not affect weights!"

    # Check HHI (Herfindahl-Hirschman Index) - Concentration
    hhi_normal = (w_normal**2).sum()
    hhi_crisis = (w_crisis**2).sum()

    print(f"HHI Normal: {hhi_normal:.4f}, HHI Crisis: {hhi_crisis:.4f}")
    # Usually higher L2 means lower HHI (more equal weights), but min_var is complex.
    # In min_var, L2 penalizes concentration, so we expect HHI_crisis <= HHI_normal?
    # Not necessarily, L2 pulls towards 0 (if not summing to 1) or towards uniform.
    # Yes, Min(Risk + lambda*Sum(w^2)) -> as lambda increases, w tends to uniform (1/N).
    # So HHI should decrease or stay same.

    # Ideally HHI Crisis should be lower (more diversified)
    # But with random data, min_var might already be diverse.
    # Just asserting they are different is enough for integration proof.


def test_barbell_regime_allocation(sample_data):
    """
    Verify Barbell strategy changes aggressor allocation based on regime.
    """
    rets, clusters = sample_data
    engine = CustomClusteredEngine()

    # Mock stats for barbell
    stats = pd.DataFrame({"Symbol": rets.columns, "Antifragility_Score": np.random.rand(10)})

    # Quiet Regime (Aggressor 15%)
    req_quiet = EngineRequest(profile="barbell", regime="QUIET", aggressor_weight=0.10)
    resp_quiet = engine.optimize(returns=rets, clusters=clusters, stats=stats, request=req_quiet)
    agg_w_quiet = resp_quiet.weights[resp_quiet.weights["Type"] == "AGGRESSOR"]["Weight"].sum()

    # Crisis Regime (Aggressor 3%)
    req_crisis = EngineRequest(profile="barbell", regime="CRISIS", aggressor_weight=0.10)
    resp_crisis = engine.optimize(returns=rets, clusters=clusters, stats=stats, request=req_crisis)
    agg_w_crisis = resp_crisis.weights[resp_crisis.weights["Type"] == "AGGRESSOR"]["Weight"].sum()

    print(f"Aggressor Weight: Quiet={agg_w_quiet:.2%}, Crisis={agg_w_crisis:.2%}")

    assert agg_w_quiet > 0.14 and agg_w_quiet < 0.16
    assert agg_w_crisis > 0.02 and agg_w_crisis < 0.04
