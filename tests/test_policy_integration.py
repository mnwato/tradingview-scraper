import pandas as pd

from tradingview_scraper.pipelines.selection.base import SelectionContext
from tradingview_scraper.pipelines.selection.filters.base import BaseFilter
from tradingview_scraper.pipelines.selection.stages.policy import SelectionPolicyStage


class MockVetoFilter(BaseFilter):
    def __init__(self, veto_symbol: str):
        self.veto_symbol = veto_symbol

    @property
    def name(self):
        return "mock_veto"

    def apply(self, context):
        return context, [self.veto_symbol]


def test_policy_stage_integration():
    # Setup data
    symbols = ["S1", "S2", "S3"]
    inference_outputs = pd.DataFrame({"alpha_score": [1.0, 0.9, 0.8]}, index=symbols)

    context = SelectionContext(
        run_id="test_policy_integration",
        raw_pool=[{"symbol": s} for s in symbols],
        inference_outputs=inference_outputs,
        returns_df=pd.DataFrame(0, index=range(10), columns=symbols),
        clusters={0: symbols},
        params={"top_n": 5},
    )

    # Instantiate with custom filters
    stage = SelectionPolicyStage(filters=[MockVetoFilter("S1")])

    ctx = stage.execute(context)

    # S1 should be vetoed by the filter
    winner_syms = [w["symbol"] for w in ctx.winners]
    assert "S1" not in winner_syms
    assert "S2" in winner_syms
    assert "S3" in winner_syms


def test_policy_stage_default_filters(monkeypatch):
    # Enable predictability vetoes for default filter test
    monkeypatch.setenv("TV_FEATURES__FEAT_PREDICTABILITY_VETOES", "1")

    # Setup data where S1 fails Predictability (high entropy)
    symbols = ["S1", "S2"]
    inference_outputs = pd.DataFrame(
        {
            "alpha_score": [1.0, 0.9],
            "entropy": [0.99, 0.5],  # S1 fails
            "efficiency": [0.8, 0.8],
            "hurst_clean": [0.5, 0.7],  # S2 is trending
            "survival": [1.0, 1.0],
            "momentum": [0.2, 0.2],
            "stability": [100.0, 100.0],
        },
        index=symbols,
    )

    context = SelectionContext(
        run_id="test_policy_defaults",
        raw_pool=[{"symbol": s, "tick_size": 0.01, "lot_size": 1.0, "price_precision": 2} for s in symbols],
        inference_outputs=inference_outputs,
        returns_df=pd.DataFrame(0, index=range(10), columns=symbols),
        clusters={0: symbols},
        params={"top_n": 5, "entropy_max_threshold": 0.9, "eci_hurdle": -1.0},  # Disable friction veto
    )

    stage = SelectionPolicyStage()  # Default filters
    ctx = stage.execute(context)

    winner_syms = [w["symbol"] for w in ctx.winners]
    assert "S1" not in winner_syms
    assert "S2" in winner_syms
