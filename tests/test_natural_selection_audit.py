import numpy as np
import pandas as pd

from scripts.natural_selection import run_selection
from tradingview_scraper.settings import get_settings


def generate_correlated_dataset(n_symbols=10, correlation=0.99, n_days=200):
    """Generates a dataset with high pairwise correlation."""
    base_returns = np.random.randn(n_days, 1) * 0.01
    noise = np.random.randn(n_days, n_symbols) * 0.01 * (1 - correlation)
    data = base_returns + noise
    symbols = [f"S{i}" for i in range(n_symbols)]
    return pd.DataFrame(data, columns=symbols, index=pd.date_range("2023-01-01", periods=n_days))


def test_audit_alpha_score_mathematical_properties():
    """
    Audit test to verify the fundamental differences between CARS 2.0 and MPS 3.0.
    CARS 2.0: Additive (High alpha can offset low liquidity).
    MPS 3.0: Multiplicative (Low survival/liquidity acts as a hard veto).
    """
    symbols = ["ALPHA_CHAMP", "FRAGILE_WINNER"]
    # Make them highly correlated to force same cluster but not identical
    data = np.random.randn(200, 1) * 0.01
    returns = pd.DataFrame(
        {"ALPHA_CHAMP": data.flatten() + np.random.randn(200) * 1e-6, "FRAGILE_WINNER": data.flatten() + np.random.randn(200) * 1e-6}, index=pd.date_range("2023-01-01", periods=200)
    )

    # Give them both positive base returns
    returns += 0.05

    raw_candidates = [
        {"symbol": "ALPHA_CHAMP", "identity": "A", "direction": "LONG", "value_traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "FRAGILE_WINNER", "identity": "B", "direction": "LONG", "value_traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
    ]

    # FRAGILE_WINNER has high alpha but near-zero survival probability
    stats_df = pd.DataFrame(
        {
            "Symbol": symbols,
            "Antifragility_Score": [0.8, 0.9],
            "Fragility_Score": [0.1, 0.1],
            "Regime_Survival_Score": [0.9, 0.01],  # The Veto Trigger
        }
    ).set_index("Symbol")

    settings = get_settings()
    settings.features.feat_dynamic_selection = False

    # --- TEST CARS 2.0 (Additive) ---
    response_v2 = run_selection(returns, raw_candidates, stats_df, top_n=1, mode="v2")

    # --- TEST MPS 3.0 (Multiplicative) ---
    response_v3 = run_selection(returns, raw_candidates, stats_df, top_n=1, mode="v3")

    selected_v3 = [w["symbol"] for w in response_v3.winners]
    assert "FRAGILE_WINNER" not in selected_v3, "MPS 3.0 failed to veto a fragile asset"
    assert "ALPHA_CHAMP" in selected_v3


def test_audit_alpha_parity_ranking():
    """Verify that ranking remains consistent when metrics are uniform."""
    symbols = [f"S{i}" for i in range(10)]
    returns = pd.DataFrame(np.random.randn(200, 10) * 0.01, columns=symbols, index=pd.date_range("2023-01-01", periods=200))

    # Force S0 to be the absolute best in every category
    returns["S0"] += 0.05

    raw_candidates = []
    for s in symbols:
        raw_candidates.append({"symbol": s, "identity": s, "direction": "LONG", "value_traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2})

    # Both systems should agree S0 is the winner if it dominates all metrics
    response_v2 = run_selection(returns, raw_candidates, None, top_n=1, mode="v2")
    response_v3 = run_selection(returns, raw_candidates, None, top_n=1, mode="v3")

    assert response_v2.winners[0]["symbol"] == "S0"
    assert response_v3.winners[0]["symbol"] == "S0"


def test_audit_numerical_stability_gate():
    """Audit the Kappa (Condition Number) veto and aggressive pruning trigger."""
    # Create near-singular matrix (identical assets)
    returns = generate_correlated_dataset(n_symbols=5, correlation=1.0)
    returns += 0.01  # Positive drift to ensure they are candidates

    symbols = list(returns.columns)
    raw_candidates = [{"symbol": s, "identity": s, "direction": "LONG", "value_traded": 1e10, "tick_size": 0.01, "lot_size": 1, "price_precision": 2} for s in symbols]

    # High Kappa should force top_n=1 even if we ask for more
    response = run_selection(returns, raw_candidates, None, top_n=3, mode="v3")

    # Check if aggressive pruning was triggered (should result in 1 winner if they are in 1 cluster)
    assert len(response.winners) == 1, f"Expected 1 winner due to high kappa, got {len(response.winners)}"


def test_audit_cluster_diversity_logic():
    """Audit that dynamic selection scales based on correlation (V2/V3 feature)."""
    settings = get_settings()
    settings.features.feat_dynamic_selection = True

    # 1. High Correlation Dataset
    returns_high = generate_correlated_dataset(n_symbols=10, correlation=0.95) + 0.01
    candidates_high = [{"symbol": s, "identity": s, "direction": "LONG", "value_traded": 1e9} for s in returns_high.columns]

    # 2. Low Correlation Dataset
    returns_low = generate_correlated_dataset(n_symbols=10, correlation=0.05) + 0.01
    candidates_low = [{"symbol": s, "identity": s, "direction": "LONG", "value_traded": 1e9} for s in returns_low.columns]

    # In low correlation, we should select more assets (closer to top_n)
    # In high correlation, we should select fewer (closer to 1)
    # We force them into 1 cluster by setting threshold high
    response_high = run_selection(returns_high, candidates_high, None, top_n=5, threshold=10.0, mode="v2")
    response_low = run_selection(returns_low, candidates_low, None, top_n=5, threshold=10.0, mode="v2")

    assert len(response_low.winners) > len(response_high.winners), f"Diversity failed: low={len(response_low.winners)}, high={len(response_high.winners)}"


def test_audit_v3_multi_veto_stack():
    """Audit the stacking of multiple vetoes (Metadata + ECI + Survival)."""
    symbols = ["HEALTHY", "NO_META", "LOW_LIQ", "EXTINCT"]
    # High volatility (0.1) ensures ECI will be high for LOW_LIQ
    returns = pd.DataFrame(np.random.randn(200, 4) * 0.1, columns=symbols, index=pd.date_range("2023-01-01", periods=200))
    # Moderate alpha (0.05)
    returns += 0.05

    raw_candidates = [
        {"symbol": "HEALTHY", "identity": "1", "direction": "LONG", "value_traded": 1e10, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "NO_META", "identity": "2", "direction": "LONG", "value_traded": 1e10},  # Missing meta
        {"symbol": "LOW_LIQ", "identity": "3", "direction": "LONG", "value_traded": 1e2, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},  # Extremely High ECI
        {"symbol": "EXTINCT", "identity": "4", "direction": "LONG", "value_traded": 1e10, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},  # Low Survival
    ]

    stats_df = pd.DataFrame(
        {
            "Symbol": symbols,
            "Antifragility_Score": 0.5,
            "Fragility_Score": 0.0,
            "Regime_Survival_Score": [1.0, 1.0, 1.0, 0.01],  # EXTINCT fails Darwin gate
        }
    ).set_index("Symbol")

    settings = get_settings()
    settings.features.feat_dynamic_selection = False

    response = run_selection(returns, raw_candidates, stats_df, top_n=5, mode="v3")

    selected = [w["symbol"] for w in response.winners]
    assert "HEALTHY" in selected
    assert "NO_META" not in selected
    assert "LOW_LIQ" not in selected
    assert "EXTINCT" not in selected
    assert len(selected) == 1
