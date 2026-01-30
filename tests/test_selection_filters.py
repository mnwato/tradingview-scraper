import numpy as np
import pandas as pd
import pytest

from tradingview_scraper.pipelines.selection.base import SelectionContext
from tradingview_scraper.pipelines.selection.filters.darwinian import DarwinianFilter
from tradingview_scraper.pipelines.selection.filters.friction import FrictionFilter
from tradingview_scraper.pipelines.selection.filters.predictability import PredictabilityFilter


@pytest.fixture
def context():
    # Setup a mock context with some candidates and data
    returns_df = pd.DataFrame({"C1": np.random.normal(0, 0.01, 100), "C2": np.random.normal(0, 0.01, 100), "C3": np.random.normal(0, 0.01, 100)})

    raw_pool = [
        {"symbol": "C1", "tick_size": 0.01, "lot_size": 1.0, "price_precision": 2, "value_traded": 1e7},
        {"symbol": "C2", "tick_size": 0.01, "lot_size": 1.0, "price_precision": 2, "value_traded": 1e7},
        {"symbol": "C3", "value_traded": 1e7},  # Missing metadata for C3
    ]

    # Symbols as Index, Metrics as Columns
    inference_outputs = pd.DataFrame(
        {"entropy": [0.5, 0.99, 0.5], "efficiency": [0.8, 0.1, 0.8], "hurst_clean": [0.5, 0.5, 0.5], "survival": [1.0, 0.05, 1.0], "momentum": [0.2, 0.2, 0.2], "stability": [100.0, 100.0, 100.0]},
        index=["C1", "C2", "C3"],
    )

    return SelectionContext(
        run_id="test_filters",
        raw_pool=raw_pool,
        returns_df=returns_df,
        inference_outputs=inference_outputs,
        params={"entropy_max_threshold": 0.9, "efficiency_min_threshold": 0.2, "eci_hurdle": 0.01, "hurst_random_walk_min": 0.45, "hurst_random_walk_max": 0.55},
    )


def test_darwinian_filter(context):
    f = DarwinianFilter()
    ctx, vetoed = f.apply(context)

    # C3 should be vetoed due to missing metadata
    assert "C3" in vetoed
    # C2 should be vetoed due to low survival (0.05 < 0.1)
    assert "C2" in vetoed
    # C1 should NOT be vetoed
    assert "C1" not in vetoed


def test_predictability_filter(context, monkeypatch):
    monkeypatch.setenv("TV_FEATURES__FEAT_PREDICTABILITY_VETOES", "1")
    f = PredictabilityFilter()
    ctx, vetoed = f.apply(context)

    # C2 should be vetoed due to high entropy (0.99 > 0.9) OR low efficiency (0.1 < 0.2)
    assert "C2" in vetoed
    # C1 and C3 should NOT be vetoed (if Hurst Random Walk is balanced)
    # Wait, Hurst=0.5 and thresholds are 0.45-0.55, so they WILL be vetoed if they are not benchmarks.
    assert "C1" in vetoed
    assert "C3" in vetoed

    # Test with benchmark exemption
    context.raw_pool[0]["is_benchmark"] = True
    ctx, vetoed2 = f.apply(context)
    assert "C1" not in vetoed2


def test_friction_filter(context):
    f = FrictionFilter()

    # Adjust C2 to have high friction (Low ADV)
    context.raw_pool[1]["value_traded"] = 1000  # Very low ADV
    # vol = 1% (stability=100)
    # ECI = 0.01 * sqrt(1e6 / 1000) = 0.01 * sqrt(1000) = 0.01 * 31.6 = 0.316
    # alpha = 0.2
    # net_alpha = 0.2 - 0.316 = -0.116 < 0.01 hurdle -> Veto

    ctx, vetoed = f.apply(context)
    assert "C2" in vetoed
    assert "C1" not in vetoed
