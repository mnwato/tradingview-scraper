import numpy as np
import pandas as pd

from tradingview_scraper.selection_engines import SelectionEngineV3_4, get_robust_correlation
from tradingview_scraper.selection_engines.base import SelectionRequest


def test_dynamic_ridge_scaling():
    # Create a highly correlated return matrix (nearly singular)
    np.random.seed(42)
    base_ret = np.random.normal(0, 0.01, 100)
    # 5 assets almost identical to base_ret
    data = {f"ASSET_{i}": base_ret + np.random.normal(0, 1e-9, 100) for i in range(5)}
    returns = pd.DataFrame(data)

    # Check initial condition number with 1% shrinkage
    corr_1pct = get_robust_correlation(returns, shrinkage=0.01)
    evs = np.linalg.eigvalsh(corr_1pct.values)
    kappa_1pct = float(evs.max() / (np.abs(evs).min() + 1e-15))
    print(f"Kappa at 1% shrinkage: {kappa_1pct}")

    # SelectionEngineV3_4 should iteratively increase shrinkage
    engine = SelectionEngineV3_4()

    # Use a low threshold to force shrinkage to trigger if kappa > threshold
    # Default is 15000 in settings, we can override in request.params
    request = SelectionRequest(
        threshold=0.5,
        top_n=5,
        params={
            "kappa_shrinkage_threshold": 100.0,  # Force shrinkage
            "default_shrinkage_intensity": 0.01,
        },
    )

    raw_candidates = [{"symbol": f"ASSET_{i}", "direction": "LONG", "tick_size": 0.01, "lot_size": 1, "price_precision": 2, "value_traded": 1e9} for i in range(5)]

    stats_df = pd.DataFrame(index=returns.columns)
    stats_df["Antifragility_Score"] = 0.5
    stats_df["Regime_Survival_Score"] = 1.0

    response = engine.select(returns, raw_candidates, stats_df, request)

    final_kappa = response.metrics["kappa"]
    final_shrinkage = response.metrics["shrinkage"]

    print(f"Final Kappa: {final_kappa}")
    print(f"Final Shrinkage: {final_shrinkage}")

    assert final_shrinkage > 0.01
    assert final_kappa < kappa_1pct
