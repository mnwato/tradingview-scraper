import unittest
from typing import Any, cast

import numpy as np
import pandas as pd

from tradingview_scraper.portfolio_engines.base import EngineRequest
from tradingview_scraper.portfolio_engines import (
    CustomClusteredEngine,
    build_engine,
    list_available_engines,
)


class TestPortfolioEngineFactory(unittest.TestCase):
    def test_list_available_engines(self):
        engines = list_available_engines()
        self.assertIn("custom", engines)

    def test_build_custom_engine(self):
        engine = build_engine("custom")
        self.assertIsInstance(engine, CustomClusteredEngine)

    def test_build_invalid_engine_raises(self):
        with self.assertRaises(ValueError):
            build_engine("non_existent_engine")


class TestCustomClusteredEngine(unittest.TestCase):
    def setUp(self):
        self.engine = CustomClusteredEngine()
        # Create synthetic returns for 10 assets over 100 days
        rng = np.random.default_rng(42)
        dates = pd.date_range("2023-01-01", periods=100)

        # Cluster 0: Low vol, Low return
        c0_rets = rng.normal(0.0001, 0.01, (100, 3))
        # Cluster 1: High vol, High return
        c1_rets = rng.normal(0.001, 0.03, (100, 3))
        # Cluster 2: Med vol, Med return
        c2_rets = rng.normal(0.0005, 0.02, (100, 4))

        all_rets = np.hstack([c0_rets, c1_rets, c2_rets])
        self.symbols = [f"S{i}" for i in range(10)]
        self.returns = pd.DataFrame(all_rets, index=dates, columns=cast(Any, self.symbols))

        self.clusters = {"0": ["S0", "S1", "S2"], "1": ["S3", "S4", "S5"], "2": ["S6", "S7", "S8", "S9"]}

        self.stats = pd.DataFrame({"Symbol": self.symbols, "Antifragility_Score": [0.1, 0.1, 0.1, 0.9, 0.9, 0.9, 0.5, 0.5, 0.5, 0.5]})

    def test_min_variance_profile(self):
        req = EngineRequest(profile="min_variance", cluster_cap=0.4)
        resp = self.engine.optimize(returns=self.returns, clusters=self.clusters, meta=None, stats=None, request=req)

        weights = resp.weights
        self.assertFalse(weights.empty)
        self.assertAlmostEqual(float(weights["Weight"].sum()), 1.0, places=5)

        # Verify cluster caps
        cluster_weights = weights.groupby("Cluster_ID")["Weight"].sum()
        for cw in cluster_weights:
            self.assertLessEqual(cw, 0.4 + 1e-6)

        # Min variance should favor Cluster 0 (lowest vol)
        self.assertTrue(cluster_weights["0"] > cluster_weights["1"])

    def test_hrp_profile(self):
        req = EngineRequest(profile="hrp", cluster_cap=0.4)
        resp = self.engine.optimize(returns=self.returns, clusters=self.clusters, meta=None, stats=None, request=req)

        weights = resp.weights
        self.assertAlmostEqual(float(weights["Weight"].sum()), 1.0, places=5)

        # HRP (Risk Parity) should distribute risk relatively evenly.
        # Cluster 1 (high vol) should have less weight than Cluster 0 (low vol).
        cluster_weights = weights.groupby("Cluster_ID")["Weight"].sum()
        self.assertTrue(cluster_weights["0"] > cluster_weights["1"])

        for cw in cluster_weights:
            self.assertLessEqual(cw, 0.4 + 1e-6)

    def test_max_sharpe_profile(self):
        req = EngineRequest(profile="max_sharpe", cluster_cap=0.4)
        resp = self.engine.optimize(returns=self.returns, clusters=self.clusters, meta=None, stats=None, request=req)

        weights = resp.weights
        self.assertAlmostEqual(float(weights["Weight"].sum()), 1.0, places=5)

        # Max Sharpe should favor high return/vol efficiency.
        # In our setup, Cluster 1 has significantly higher returns.
        cluster_weights = weights.groupby("Cluster_ID")["Weight"].sum()
        # It should be capped or at least higher than min_var's allocation to Cluster 1
        self.assertTrue(cluster_weights["1"] > 0.01)

    def test_barbell_profile(self):
        req = EngineRequest(profile="barbell", cluster_cap=0.4, aggressor_weight=0.3, max_aggressor_clusters=1)

        resp = self.engine.optimize(returns=self.returns, clusters=self.clusters, meta=None, stats=self.stats, request=req)

        weights = resp.weights
        self.assertAlmostEqual(float(weights["Weight"].sum()), 1.0, places=5)

        # Check for aggressor tag
        has_aggressor = weights["Cluster_Label"].fillna("").str.contains("AGGRESSOR").any()
        self.assertTrue(has_aggressor)

        # Aggressor cluster (Cluster 1 has highest antifragility)
        agg_rows = weights[weights["Cluster_Label"] == "AGGRESSOR"]
        self.assertAlmostEqual(float(agg_rows["Weight"].sum()), 0.3, places=5)
        self.assertTrue((agg_rows["Cluster_ID"] == "1").all())

    def test_max_sharpe_return_efficiency(self):
        # Create 2 clusters with same vol but different returns
        rng = np.random.default_rng(456)
        dates = pd.date_range("2023-01-01", periods=100)

        # High return cluster
        high_ret = rng.normal(0.005, 0.02, (100, 2))
        # Low return cluster
        low_ret = rng.normal(0.0001, 0.02, (100, 2))

        returns = pd.DataFrame(np.hstack([high_ret, low_ret]), index=dates, columns=cast(Any, ["H1", "H2", "L1", "L2"]))
        clusters = {"HIGH": ["H1", "H2"], "LOW": ["L1", "L2"]}

        req = EngineRequest(profile="max_sharpe", cluster_cap=0.8)
        resp = self.engine.optimize(returns=returns, clusters=clusters, meta=None, stats=None, request=req)

        weights = resp.weights.groupby("Cluster_ID")["Weight"].sum()
        # High return cluster should have significantly more weight
        self.assertTrue(weights["HIGH"] > weights["LOW"])

    def test_hrp_volatility_inverse_weighting(self):
        # Create 2 clusters: one with low vol, one with high vol
        rng = np.random.default_rng(123)
        dates = pd.date_range("2023-01-01", periods=100)

        # Low vol cluster
        low_vol = rng.normal(0, 0.01, (100, 2))
        # High vol cluster
        high_vol = rng.normal(0, 0.05, (100, 2))

        returns = pd.DataFrame(np.hstack([low_vol, high_vol]), index=dates, columns=cast(Any, ["L1", "L2", "H1", "H2"]))
        clusters = {"LOW": ["L1", "L2"], "HIGH": ["H1", "H2"]}

        req = EngineRequest(profile="hrp", cluster_cap=0.8)
        resp = self.engine.optimize(returns=returns, clusters=clusters, meta=None, stats=None, request=req)

        weights = resp.weights.groupby("Cluster_ID")["Weight"].sum()
        # High vol cluster should have less weight
        self.assertTrue(weights["LOW"] > weights["HIGH"])

    def test_empty_universe_graceful_failure(self):
        req = EngineRequest(profile="min_variance")
        resp = self.engine.optimize(returns=pd.DataFrame(), clusters={}, meta=None, stats=None, request=req)
        self.assertTrue(resp.weights.empty)
        self.assertIn("empty universe", resp.warnings)

    def test_single_asset_universe(self):
        req = EngineRequest(profile="min_variance", cluster_cap=0.5)
        returns = pd.DataFrame({"S0": [0.01, -0.01, 0.02]}, index=pd.date_range("2023-01-01", periods=3))
        clusters = {"0": ["S0"]}

        resp = self.engine.optimize(returns=returns, clusters=clusters, meta=None, stats=None, request=req)
        # For single asset, cap is adjusted to 1.0 by _effective_cap
        self.assertAlmostEqual(float(resp.weights["Weight"].sum()), 1.0, places=5)
        self.assertEqual(len(resp.weights), 1)

    def test_equal_weight_profile(self):
        # This profile is handled by MarketBaselineEngine
        from tradingview_scraper.portfolio_engines import MarketBaselineEngine

        engine = MarketBaselineEngine()

        returns = pd.DataFrame(np.random.randn(10, 4), columns=cast(Any, ["A", "B", "C", "D"]))
        req = EngineRequest(profile="equal_weight")

        resp = engine.optimize(returns=returns, clusters={}, meta=None, stats=None, request=req)
        weights = resp.weights

        self.assertEqual(len(weights), 4)
        self.assertAlmostEqual(float(weights["Weight"].sum()), 1.0, places=5)
        self.assertTrue((weights["Weight"] == 0.25).all())
        self.assertTrue((weights["Cluster_ID"] == "MARKET_EW").all())


if __name__ == "__main__":
    unittest.main()
