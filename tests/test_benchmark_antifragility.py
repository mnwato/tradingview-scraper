import numpy as np
import pandas as pd

from tradingview_scraper.utils.metrics import (
    calculate_antifragility_distribution,
    calculate_antifragility_stress,
)


def _series(vals: np.ndarray) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=len(vals), freq="D")
    return pd.Series(vals, index=idx)


def test_antifragility_distribution_ranks_positive_skew_higher():
    rng = np.random.default_rng(0)
    n = 200

    pos = rng.normal(0.0, 0.005, n)
    pos[rng.choice(n, size=10, replace=False)] += 0.05

    neg = rng.normal(0.0, 0.005, n)
    neg[rng.choice(n, size=10, replace=False)] -= 0.05

    res_pos = calculate_antifragility_distribution(_series(pos), q=0.95, min_obs=100, min_tail=10)
    res_neg = calculate_antifragility_distribution(_series(neg), q=0.95, min_obs=100, min_tail=10)

    assert res_pos["is_sufficient"] is True
    assert res_neg["is_sufficient"] is True
    assert res_pos["af_dist"] > res_neg["af_dist"]


def test_antifragility_stress_detects_positive_crisis_alpha():
    rng = np.random.default_rng(1)
    n = 200

    ref = _series(rng.normal(0.0, 0.01, n))
    cut = float(ref.quantile(0.10))
    stress_mask = ref <= cut

    strat = ref.copy()
    strat.loc[stress_mask] = strat.loc[stress_mask] + 0.01

    res = calculate_antifragility_stress(strat, ref, q_stress=0.10, min_obs=100, min_stress=10)

    assert res["is_sufficient"] is True
    assert res["stress_alpha"] > 0.008
    assert res["stress_delta"] > 0.0
    assert res["stress_hit_rate"] > 0.95


def test_antifragility_distribution_insufficient_data():
    s = _series(np.zeros(50, dtype=float))
    res = calculate_antifragility_distribution(s, min_obs=100)
    assert res["is_sufficient"] is False
