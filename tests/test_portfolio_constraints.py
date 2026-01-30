from unittest.mock import patch

import numpy as np
import pandas as pd

from tradingview_scraper.portfolio_engines.base import EngineRequest
from tradingview_scraper.portfolio_engines.impl.custom import CustomClusteredEngine
from tradingview_scraper.utils.synthesis import calculate_beta


def test_market_neutral_beta_constraint():
    with patch("tradingview_scraper.portfolio_engines.impl.custom.get_settings") as mock_settings:
        mock_settings.return_value.features.feat_market_neutral = True

        np.random.seed(42)
        # Benchmark returns
        bench_rets = pd.Series(np.random.normal(0.01, 0.01, 200))

        # Asset A: Beta ~ 2.0, high positive drift
        rets_a = 2.0 * bench_rets + np.random.normal(0.01, 0.005, 200)
        # Asset B: Beta ~ 0.5, small positive drift
        rets_b = 0.5 * bench_rets + np.random.normal(0.001, 0.005, 200)
        # Asset C: Beta ~ -1.5, negative drift
        rets_c = -1.5 * bench_rets + np.random.normal(-0.01, 0.005, 200)

        returns = pd.DataFrame({"BETA_HIGH": rets_a, "BETA_LOW": rets_b, "BETA_NEG": rets_c, "BENCH": bench_rets})

        clusters = {"1": ["BETA_HIGH"], "2": ["BETA_LOW"], "3": ["BETA_NEG"]}
        meta = {s: {"symbol": s, "direction": "LONG"} for s in returns.columns}

        engine = CustomClusteredEngine()

        # 1. Unconstrained - using a large cap to ensure feasibility
        req_un = EngineRequest(profile="max_sharpe", market_neutral=False, cluster_cap=0.8)
        resp_un = engine.optimize(returns=returns, clusters=clusters, meta=meta, request=req_un)
        w_un = resp_un.weights.set_index("Symbol")["Weight"]

        # 2. Neutral - using a large cap to allow hedging
        b_rets_input = pd.Series(returns["BENCH"])
        req_neu = EngineRequest(profile="max_sharpe", market_neutral=True, benchmark_returns=b_rets_input, cluster_cap=0.8)
        resp_neu = engine.optimize(returns=returns, clusters=clusters, meta=meta, request=req_neu)
        w_neu = resp_neu.weights.set_index("Symbol")["Weight"]

        s_high = pd.Series(returns["BETA_HIGH"])
        s_low = pd.Series(returns["BETA_LOW"])
        s_neg = pd.Series(returns["BETA_NEG"])
        s_bench = pd.Series(returns["BENCH"])

        beta_a = calculate_beta(s_high, s_bench)
        beta_b = calculate_beta(s_low, s_bench)
        beta_c = calculate_beta(s_neg, s_bench)

        w_h_un = float(w_un.get("BETA_HIGH", 0.0))
        w_l_un = float(w_un.get("BETA_LOW", 0.0))
        w_n_un = float(w_un.get("BETA_NEG", 0.0))
        pb_un = w_h_un * beta_a + w_l_un * beta_b + w_n_un * beta_c

        w_h_neu = float(w_neu.get("BETA_HIGH", 0.0))
        w_l_neu = float(w_neu.get("BETA_LOW", 0.0))
        w_n_neu = float(w_neu.get("BETA_NEG", 0.0))
        pb_neu = w_h_neu * beta_a + w_l_neu * beta_b + w_n_neu * beta_c

        print(f"\nBetas: A={beta_a:.2f}, B={beta_b:.2f}, C={beta_c:.2f}")
        print(f"Port Beta Un: {pb_un:.4f}")
        print(f"Port Beta Neu: {pb_neu:.4f}")

        assert abs(pb_neu) <= 0.16  # matched to our internal tolerance of 0.15
        assert abs(pb_neu) < abs(pb_un)


def test_market_neutral_flag_disabled():
    """Verify that market neutral constraint is ignored when feat_market_neutral is False."""
    with patch("tradingview_scraper.portfolio_engines.impl.custom.get_settings") as mock_settings:
        mock_settings.return_value.features.feat_market_neutral = False

        np.random.seed(42)
        bench_rets = pd.Series(np.random.normal(0.01, 0.01, 200))
        rets_a = 2.0 * bench_rets + np.random.normal(0.01, 0.005, 200)
        rets_b = 0.5 * bench_rets + np.random.normal(0.001, 0.005, 200)
        returns = pd.DataFrame({"BETA_HIGH": rets_a, "BETA_LOW": rets_b, "BENCH": bench_rets})

        clusters = {"1": ["BETA_HIGH"], "2": ["BETA_LOW"]}
        meta = {s: {"symbol": s, "direction": "LONG"} for s in returns.columns}

        engine = CustomClusteredEngine()

        # 1. Unconstrained
        req_un = EngineRequest(profile="max_sharpe", market_neutral=False, cluster_cap=0.8)
        resp_un = engine.optimize(returns=returns, clusters=clusters, meta=meta, request=req_un)
        w_un = resp_un.weights.set_index("Symbol")["Weight"]

        # 2. Requested Neutral but flag is OFF
        b_rets_input = pd.Series(returns["BENCH"])
        req_neu = EngineRequest(profile="max_sharpe", market_neutral=True, benchmark_returns=b_rets_input, cluster_cap=0.8)
        resp_neu = engine.optimize(returns=returns, clusters=clusters, meta=meta, request=req_neu)
        w_neu = resp_neu.weights.set_index("Symbol")["Weight"]

        # Weights should be identical since constraint was skipped
        pd.testing.assert_series_equal(w_un, w_neu)
