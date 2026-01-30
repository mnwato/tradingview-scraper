import numpy as np
import pandas as pd

from tradingview_scraper.selection_engines.base import SelectionRequest
from tradingview_scraper.selection_engines.impl.v3_4_htr import SelectionEngineV3_4


def test_toxicity_hard_stop():
    # Generate some returns
    np.random.seed(42)
    # Good trend
    ret_a = np.linspace(0, 0.1, 500) + np.random.normal(0, 0.001, 500)
    # White noise (high entropy)
    ret_b = np.random.normal(0, 1.0, 500)

    returns = pd.DataFrame({"GOOD": ret_a, "TOXIC": ret_b})

    # Mock candidates
    raw_candidates = [
        {"symbol": "GOOD", "direction": "LONG", "tick_size": 0.01, "lot_size": 1, "price_precision": 2, "value_traded": 1e9},
        {"symbol": "TOXIC", "direction": "LONG", "tick_size": 0.01, "lot_size": 1, "price_precision": 2, "value_traded": 1e9},
    ]

    engine = SelectionEngineV3_4()
    request = SelectionRequest(threshold=0.5, top_n=1, params={"relaxation_stage": 3})

    stats_df = pd.DataFrame(index=pd.Index(["GOOD", "TOXIC"]))
    stats_df["Antifragility_Score"] = 0.5
    stats_df["Regime_Survival_Score"] = 1.0

    response = engine.select(returns, raw_candidates, stats_df, request)
    winner_syms = [w["symbol"] for w in response.winners]

    # Check entropy in the response metrics
    toxic_entropy = response.metrics["raw_metrics"]["entropy"]["TOXIC"]
    print(f"Toxic Entropy: {toxic_entropy}")

    # GOOD should be in winners
    assert "GOOD" in winner_syms

    # TOXIC should NOT be in winners even in Stage 3 if entropy > 0.999
    if toxic_entropy > 0.999:
        assert "TOXIC" not in winner_syms


def test_balanced_selection_min_pool_respects_toxicity():
    # Verify that Balanced Selection (Stage 4) still respects toxicity stop
    np.random.seed(42)
    # Generate 20 assets, all noisy
    data = {f"NOISE_{i}": np.random.normal(0, 0.1, 500) for i in range(20)}
    returns = pd.DataFrame(data)

    raw_candidates = [{"symbol": f"NOISE_{i}", "direction": "LONG", "tick_size": 0.01, "lot_size": 1, "price_precision": 2, "value_traded": 1e9} for i in range(20)]

    engine = SelectionEngineV3_4()
    request = SelectionRequest(threshold=0.5, top_n=1, params={"relaxation_stage": 4})

    stats_df = pd.DataFrame(index=pd.Index(returns.columns))
    stats_df["Antifragility_Score"] = 0.5
    stats_df["Regime_Survival_Score"] = 1.0

    response = engine.select(returns, raw_candidates, stats_df, request)

    for w in response.winners:
        sym = w["symbol"]
        ent = response.metrics["raw_metrics"]["entropy"][sym]
        assert ent <= 0.999, f"Winner {sym} is toxic (Entropy={ent})"
