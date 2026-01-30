from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from tradingview_scraper.selection_engines import SelectionEngineV3_1, SelectionEngineV3_2
from tradingview_scraper.selection_engines.base import SelectionRequest
from tradingview_scraper.settings import FeatureFlags


def test_v3_2_logmps_parity_with_v3_1():
    """Verify that v3.2 Log-MPS matches v3.1 when weights are neutral."""
    np.random.seed(42)
    n_days = 100
    n_syms = 10
    returns = pd.DataFrame(np.random.randn(n_days, n_syms) * 0.01 + 0.001, columns=[f"S{i}" for i in range(n_syms)])

    raw_candidates = [{"symbol": f"S{i}", "direction": "LONG", "Value.Traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2} for i in range(n_syms)]

    request = SelectionRequest(top_n=3, threshold=0.5, max_clusters=5, min_momentum_score=-1.0)

    engine_v31 = SelectionEngineV3_1()
    engine_v32 = SelectionEngineV3_2()

    # Run v3.1
    res_v31 = engine_v31.select(returns, raw_candidates, stats_df=None, request=request)

    # Run v3.2 with flag ON and neutral weights (parity mode)
    with patch("tradingview_scraper.selection_engines.get_settings") as mock_get:
        parity_weights = {
            "momentum": 1.0,
            "stability": 1.0,
            "liquidity": 1.0,
            "antifragility": 1.0,
            "survival": 1.0,
            "efficiency": 1.0,
            "entropy": 0.0,
            "hurst_clean": 0.0,
        }
        mock_get.return_value.features = FeatureFlags(feat_selection_logmps=True, weights_global=parity_weights)
        res_v32 = engine_v32.select(returns, raw_candidates, stats_df=None, request=request)

    assert [w["symbol"] for w in res_v32.winners] == [w["symbol"] for w in res_v31.winners]

    # Check alpha scores parity (should be very close)
    scores_v31 = res_v31.metrics["alpha_scores"]
    scores_v32 = res_v32.metrics["alpha_scores"]

    for sym in scores_v31:
        assert pytest.approx(scores_v31[sym], rel=1e-5) == scores_v32[sym]


def test_v3_2_flag_off_fallback():
    """Verify that v3.2 falls back to v3.1 if flag is off."""
    engine_v32 = SelectionEngineV3_2()

    with patch("tradingview_scraper.selection_engines.get_settings") as mock_get:
        mock_get.return_value.features = FeatureFlags(feat_selection_logmps=False)
        # Using MagicMock for dependencies to just check call
        with patch("tradingview_scraper.selection_engines.SelectionEngineV3_1") as MockV31:
            mock_v31_inst = MockV31.return_value
            engine_v32.select(pd.DataFrame(), [], None, MagicMock())
            assert mock_v31_inst.select.called
