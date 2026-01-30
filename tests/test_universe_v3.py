from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import yaml

from scripts.audit_antifragility import calculate_regime_survival
from tradingview_scraper.utils.scoring import calculate_mps_score, calculate_survival_probability, map_to_probability, rank_series


def test_rank_series():
    s = pd.Series([10, 20, 30, 40], index=["A", "B", "C", "D"])
    ranks = rank_series(s)
    assert ranks["A"] == 0.25
    assert ranks["D"] == 1.0


def test_map_to_probability_rank():
    s = pd.Series([10, 20, 30], index=["A", "B", "C"])
    probs = map_to_probability(s, method="rank")
    # Ranks: 1, 2, 3 -> mapped to 0.01, 0.505, 1.0
    assert probs["A"] == pytest.approx(0.01)
    assert probs["B"] == pytest.approx(0.505)
    assert probs["C"] == pytest.approx(1.0)


def test_calculate_mps_score_veto():
    # Test that a failing component significantly drags down the score
    # We use a larger universe to make rank behavior more predictable
    symbols = [f"S{i}" for i in range(10)]

    # S0 is top alpha but bottom liquidity
    alpha = pd.Series(np.linspace(0, 100, 10), index=symbols)  # S0=0, S9=100
    liquidity = pd.Series([0] + [10] * 9, index=symbols)  # S0=0 (Fail), others=10

    metrics = {"alpha": alpha, "liquidity": liquidity}

    scores = calculate_mps_score(metrics)

    # S0 failed liquidity (rank 1), so it should be near bottom regardless of alpha
    # S0 liquidity rank = 1 -> prob 0.01
    # S0 alpha rank = 1 -> prob 0.01
    # S0 total = 0.0001

    # S9 liquidity rank = 10 -> prob 1.0
    # S9 alpha rank = 10 -> prob 1.0
    # S9 total = 1.0

    assert scores["S0"] < scores["S9"]
    assert scores["S0"] == pytest.approx(0.0001)


def test_calculate_survival_probability():
    bars = pd.Series([252, 10, 1000], index=["A", "B", "C"])
    gap_pct = pd.Series([0.0, 0.1, 0.0], index=["A", "B", "C"])
    regime = pd.Series([1.0, 0.5, 1.0], index=["A", "B", "C"])

    survival = calculate_survival_probability(bars, gap_pct, regime)

    # 252 bars should be ~0.5 hist prob
    # 1 / (1 + (252/252)**2) = 1/2 = 0.5
    assert survival["A"] == pytest.approx(0.5, rel=1e-5)
    # Short history should be very low
    assert survival["B"] < survival["A"]
    # Long history, no gaps, good regime should be high
    assert survival["C"] > survival["A"]


def test_calculate_regime_survival(tmp_path):
    # Setup dummy returns covering the event window
    dates = pd.date_range("2024-07-25", periods=20, freq="D")
    returns = pd.DataFrame(
        {
            "ALIVE": [0.01] * 20,
            "DEAD": [0.0] * 20,  # 100% gaps during the event
        },
        index=dates,
    )

    # Setup dummy stress calendar
    cal_file = tmp_path / "stress_calendar.yaml"
    cal_content = {"stress_events": [{"id": "TEST_AUG", "start": "2024-08-01", "end": "2024-08-10"}]}
    with open(cal_file, "w") as f:
        yaml.dump(cal_content, f)

    with patch("scripts.audit_antifragility.Path", return_value=cal_file):
        survival = calculate_regime_survival(returns)

    assert "ALIVE" in survival["Symbol"].values
    alive_score = survival.loc[survival["Symbol"] == "ALIVE", "Regime_Survival_Score"].values[0]
    dead_score = survival.loc[survival["Symbol"] == "DEAD", "Regime_Survival_Score"].values[0]

    assert alive_score == 1.0
    assert dead_score == 0.0
