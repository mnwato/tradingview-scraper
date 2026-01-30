import numpy as np
import pandas as pd

from tradingview_scraper.portfolio_engines.base import EngineRequest, ProfileName
from tradingview_scraper.portfolio_engines import CustomClusteredEngine
from tradingview_scraper.settings import get_settings


def test_turnover_penalty_reduction():
    """Verify that turnover penalty reduces trade size."""
    engine = CustomClusteredEngine()

    # Setup data
    assets = ["A", "B", "C"]
    returns = pd.DataFrame(np.random.normal(0.001, 0.02, (100, 3)), columns=assets, index=pd.date_range("2023-01-01", periods=100))  # type: ignore
    clusters = {"1": ["A", "B"], "2": ["C"]}

    # Previous weights (Current state)
    # Portfolio is 100% in cluster 2 (Asset C)
    prev_weights = pd.Series({"A": 0.0, "B": 0.0, "C": 1.0})

    # Case 1: Penalty DISABLED
    settings = get_settings()
    settings.features.feat_turnover_penalty = False

    req_no_penalty = EngineRequest(profile=cast(ProfileName, "min_variance"), cluster_cap=0.5, prev_weights=prev_weights)
    res_no = engine.optimize(returns=returns, clusters=clusters, meta={}, stats=None, request=req_no_penalty)
    w_no = res_no.weights.set_index("Symbol")["Weight"]

    # Case 2: Penalty ENABLED
    settings.features.feat_turnover_penalty = True
    req_with_penalty = EngineRequest(profile=cast(ProfileName, "min_variance"), cluster_cap=0.5, prev_weights=prev_weights)
    res_with = engine.optimize(returns=returns, clusters=clusters, meta={}, stats=None, request=req_with_penalty)
    w_with = res_with.weights.set_index("Symbol")["Weight"]

    # Calculate churn: sum(|w_new - w_prev|)
    # Fill missing assets with 0
    def calc_churn(w_new, w_old):
        all_syms = set(w_new.index) | set(w_old.index)
        w_n = w_new.reindex(all_syms).fillna(0.0)
        w_o = w_old.reindex(all_syms).fillna(0.0)
        return float(np.abs(w_n - w_o).sum())

    churn_no = calc_churn(w_no, prev_weights)
    churn_with = calc_churn(w_with, prev_weights)

    print(f"Churn without penalty: {churn_no:.4f}")
    print(f"Churn with penalty: {churn_with:.4f}")

    # Churn with penalty should be strictly less than or equal to churn without
    # (Usually significantly less if the optimal shifts far from prev_weights)
    # Using 1e-5 to allow for solver numerical noise when results are nearly identical
    assert churn_with <= churn_no + 1e-5

    # Reset settings
    settings.features.feat_turnover_penalty = False


from typing import cast
