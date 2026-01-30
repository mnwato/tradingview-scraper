import pandas as pd
import numpy as np
import pytest
from tradingview_scraper.pipelines.selection.rankers.regime import StrategyRegimeRanker
from tradingview_scraper.pipelines.selection.base import SelectionContext


@pytest.fixture
def ranker():
    return StrategyRegimeRanker(strategy="trend_following", enable_audit_log=False)


def create_trending_rets(length=100, drift=0.01, vol=0.01):
    """Positive Autocorrelation + Drift"""
    rets = [0.0]
    for _ in range(length - 1):
        # r_t = drift + phi*r_{t-1} + noise
        r = drift + 0.5 * rets[-1] + np.random.normal(0, vol)
        rets.append(r)
    return pd.Series(rets)


def create_meanrev_rets(length=100, vol=0.01):
    """Negative Autocorrelation"""
    rets = [0.0]
    for _ in range(length - 1):
        # r_t = -phi*r_{t-1} + noise
        r = -0.8 * rets[-1] + np.random.normal(0, vol)
        rets.append(r)
    return pd.Series(rets)


def test_base_ranker_interface():
    """Verify implementation of BaseRanker.rank()"""
    np.random.seed(42)
    t_rets = create_trending_rets(length=100)
    m_rets = create_meanrev_rets(length=100)
    df = pd.DataFrame({"TREND": t_rets, "MEANREV": m_rets})

    # Mock context
    context = SelectionContext(
        run_id="test",
        params={},
        raw_pool=[],
        returns_df=df,
        feature_store=pd.DataFrame(),
        inference_outputs=pd.DataFrame(),
        model_metadata={},
        clusters={},
        winners=[{"symbol": "TREND"}, {"symbol": "MEANREV"}],
        strategy_atoms=[],
        composition_map={},
        audit_trail=[],
    )

    ranker = StrategyRegimeRanker(strategy="trend_following")
    sorted_ids = ranker.rank(["TREND", "MEANREV"], context)

    assert sorted_ids == ["TREND", "MEANREV"]

    ranker_mr = StrategyRegimeRanker(strategy="mean_reversion")
    sorted_ids_mr = ranker_mr.rank(["TREND", "MEANREV"], context)
    assert sorted_ids_mr == ["MEANREV", "TREND"]


def test_trend_ranking(ranker):
    """Verify Trend strategy favors trending assets."""
    np.random.seed(42)

    # 1. Trending Asset
    t_rets = create_trending_rets(length=100, drift=0.02, vol=0.005)

    # 2. Mean Reverting Asset
    m_rets = create_meanrev_rets(length=100, vol=0.02)

    df = pd.DataFrame({"TREND": t_rets, "MEANREV": m_rets})
    cands = [{"symbol": "TREND"}, {"symbol": "MEANREV"}]

    ranked = ranker.rank_metadata(cands, df, strategy="trend_following")

    assert ranked[0]["symbol"] == "TREND"
    assert ranked[0]["rank_score"] > ranked[1]["rank_score"]
    assert ranked[0]["asset_hurst"] > 0.5


def test_meanrev_ranking(ranker):
    """Verify MeanRev strategy favors ranging assets."""
    np.random.seed(42)

    # 1. Trending Asset
    t_rets = create_trending_rets(length=100, drift=0.02, vol=0.005)

    # 2. Mean Reverting Asset
    m_rets = create_meanrev_rets(length=100, vol=0.02)

    df = pd.DataFrame({"TREND": t_rets, "MEANREV": m_rets})
    cands = [{"symbol": "TREND"}, {"symbol": "MEANREV"}]

    ranked = ranker.rank_metadata(cands, df, strategy="mean_reversion")

    assert ranked[0]["symbol"] == "MEANREV"
    assert ranked[0]["rank_score"] > ranked[1]["rank_score"]
    assert ranked[0]["asset_hurst"] < 0.5


def test_selection_integration(ranker):
    """Verify that ranking correctly affects alpha scores in a mock selection flow."""
    # 1. Setup Data
    np.random.seed(42)
    t_rets = create_trending_rets(length=100)
    m_rets = create_meanrev_rets(length=100)
    df = pd.DataFrame({"TREND": t_rets, "MEANREV": m_rets})

    # 2. Mock Alpha Scores (Equal initial scores)
    alpha_scores = pd.Series(1.0, index=["TREND", "MEANREV"])

    # 3. Apply Ranker
    cands = [{"symbol": "TREND"}, {"symbol": "MEANREV"}]

    # Trend Strategy
    ranked_t = ranker.rank_metadata(cands, df, strategy="trend_following")
    rank_map_t = {c["symbol"]: c for c in ranked_t}

    alpha_t = alpha_scores.copy()
    for s in alpha_t.index:
        multiplier = max(0.1, 1.0 + rank_map_t[s]["rank_score"])
        alpha_t.loc[s] *= multiplier

    assert alpha_t["TREND"] > alpha_t["MEANREV"]

    # Mean Rev Strategy
    ranked_m = ranker.rank_metadata(cands, df, strategy="mean_reversion")
    rank_map_m = {c["symbol"]: c for c in ranked_m}

    alpha_m = alpha_scores.copy()
    for s in alpha_m.index:
        multiplier = max(0.1, 1.0 + rank_map_m[s]["rank_score"])
        alpha_m.loc[s] *= multiplier

    assert alpha_m["MEANREV"] > alpha_m["TREND"]
