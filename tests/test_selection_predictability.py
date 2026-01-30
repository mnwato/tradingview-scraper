import numpy as np
import pandas as pd

from tradingview_scraper.selection_engines import SelectionEngineV3
from tradingview_scraper.selection_engines.base import SelectionRequest


def test_selection_v3_predictability_vetoes():
    engine = SelectionEngineV3()

    # 100 days of returns for 4 symbols
    # SYM1: Normal trend
    # SYM2: High entropy (noise)
    # SYM3: Low efficiency (chop)
    # SYM4: Random walk (Hurst ~ 0.5)

    np.random.seed(42)
    n_days = 100

    # SYM1: Clean trend (returns increasing)
    sym1_rets = np.linspace(0.001, 0.005, n_days) + np.random.randn(n_days) * 0.00001

    # SYM2: High entropy noise
    sym2_rets = np.random.randn(n_days) * 0.01

    # SYM3: Low efficiency (big moves but net zero)
    sym3_rets = np.array([0.01, -0.01] * (n_days // 2))

    # SYM4: Random Walk
    # (Actually white noise is a random walk in prices, but Hurst of white noise is 0.5)
    # np.random.randn is usually 0.5.
    sym4_rets = np.random.randn(n_days) * 0.005

    returns = pd.DataFrame({"SYM1": sym1_rets, "SYM2": sym2_rets, "SYM3": sym3_rets, "SYM4": sym4_rets})

    raw_candidates = [
        {"symbol": "SYM1", "direction": "LONG", "Value.Traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "SYM2", "direction": "LONG", "Value.Traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "SYM3", "direction": "LONG", "Value.Traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "SYM4", "direction": "LONG", "Value.Traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
    ]

    request = SelectionRequest(top_n=1, threshold=0.5, max_clusters=5, min_momentum_score=-1.0)

    from unittest.mock import patch

    from tradingview_scraper.settings import FeatureFlags

    with patch("tradingview_scraper.selection_engines.get_settings") as mock_get:
        mock_get.return_value.features = FeatureFlags(feat_predictability_vetoes=True)
        response = engine.select(returns, raw_candidates, stats_df=None, request=request)

    # Check vetoes
    vetoes = response.vetoes

    # We expect SYM2, SYM3, SYM4 to potentially be vetoed depending on calculated scores
    # Let's print them for debugging
    for sym, reasons in vetoes.items():
        print(f"{sym}: {reasons}")

    # SYM1 should be a winner
    winners = [w["symbol"] for w in response.winners]
    assert "SYM1" in winners

    # Verify that at least some vetoes related to predictability are present
    predictability_vetoes = False
    for reasons in vetoes.values():
        if any(r for r in reasons if "Entropy" in r or "Efficiency" in r or "Hurst" in r):
            predictability_vetoes = True
            break

    assert predictability_vetoes, "No predictability vetoes were triggered"


def test_selection_v3_feature_flags():
    """Verify that predictability vetoes are only applied when the feature flag is enabled."""
    engine = SelectionEngineV3()

    np.random.seed(42)
    n_days = 100
    # Create a noisy series that WOULD be vetoed if flag is on
    noisy_rets = np.random.randn(n_days) * 0.01 + 0.1  # High positive mean to pass alpha gate
    clean_rets = np.linspace(0.001, 0.005, n_days) + 0.1

    returns = pd.DataFrame({"NOISY": noisy_rets, "CLEAN": clean_rets})
    raw_candidates = [
        {"symbol": "NOISY", "direction": "LONG", "Value.Traded": 1e15, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "CLEAN", "direction": "LONG", "Value.Traded": 1e15, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
    ]
    request = SelectionRequest(top_n=1, threshold=0.5, max_clusters=5, min_momentum_score=-1.0)

    from unittest.mock import patch

    from tradingview_scraper.settings import FeatureFlags

    # 1. Flag OFF (Default)
    with patch("tradingview_scraper.selection_engines.get_settings") as mock_get:
        mock_get.return_value.features = FeatureFlags(feat_predictability_vetoes=False)
        response = engine.select(returns, raw_candidates, stats_df=None, request=request)
        # Should NOT be vetoed for entropy
        assert "NOISY" not in response.vetoes or not any("Entropy" in r for r in response.vetoes["NOISY"])
        # We expect 2 winners (or 1 depending on clustering and top_n, but specifically NOISY should not be vetoed)
        winners = [w["symbol"] for w in response.winners]
        assert "NOISY" in winners or "NOISY" not in response.vetoes

    # 2. Flag ON
    with patch("tradingview_scraper.selection_engines.get_settings") as mock_get:
        # Lower threshold to ensure veto
        mock_get.return_value.features = FeatureFlags(feat_predictability_vetoes=True, entropy_max_threshold=0.5)
        response = engine.select(returns, raw_candidates, stats_df=None, request=request)
        # SHOULD be vetoed
        assert "NOISY" in response.vetoes
        assert any("Entropy" in r for r in response.vetoes["NOISY"])


def test_selection_v3_1_feature_flags():
    """Verify that V3.1 also respects the predictability feature flags."""
    from tradingview_scraper.selection_engines import SelectionEngineV3_1

    engine = SelectionEngineV3_1()

    np.random.seed(42)
    n_days = 100
    noisy_rets = np.random.randn(n_days) * 0.01 + 0.1
    clean_rets = np.linspace(0.001, 0.005, n_days) + 0.1

    returns = pd.DataFrame({"NOISY": noisy_rets, "CLEAN": clean_rets})
    raw_candidates = [
        {"symbol": "NOISY", "direction": "LONG", "Value.Traded": 1e15, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "CLEAN", "direction": "LONG", "Value.Traded": 1e15, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
    ]
    request = SelectionRequest(top_n=1, threshold=0.5, max_clusters=5, min_momentum_score=-1.0)

    from unittest.mock import patch

    from tradingview_scraper.settings import FeatureFlags

    # Flag ON
    with patch("tradingview_scraper.selection_engines.get_settings") as mock_get:
        mock_get.return_value.features = FeatureFlags(feat_predictability_vetoes=True, entropy_max_threshold=0.5)
        response = engine.select(returns, raw_candidates, stats_df=None, request=request)
        assert "NOISY" in response.vetoes
        assert any("Entropy" in r for r in response.vetoes["NOISY"])
