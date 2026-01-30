import unittest

import numpy as np
import pandas as pd

from tradingview_scraper.risk import BarbellOptimizer, ShrinkageCovariance


class TestShrinkageCovariance(unittest.TestCase):
    # ... existing tests ...

    def test_ledoit_wolf_estimate(self):
        # Create a small, potentially singular dataset

        # 5 assets, but only 10 days of data

        data = np.random.normal(0, 0.01, (10, 5))

        returns = pd.DataFrame(data)

        estimator = ShrinkageCovariance()

        cov_shrunk = estimator.estimate(returns)

        self.assertEqual(cov_shrunk.shape, (5, 5))

        # Naive covariance might be ill-conditioned, shrunk should be better

        # Just verify it's a valid positive semi-definite matrix

        self.assertTrue(np.all(np.linalg.eigvals(cov_shrunk) > 0))


class TestBarbellOptimizer(unittest.TestCase):
    def test_optimize_regime_aware(self):
        # Setup returns for 5 core + 2 aggressors

        data = np.random.normal(0, 0.01, (30, 7))

        columns = pd.Index([f"C{i}" for i in range(5)] + ["A1", "A2"])
        returns = pd.DataFrame(data, columns=columns)

        # Mock Antifragility Stats

        stats = pd.DataFrame(
            [
                {"Symbol": "A1", "Antifragility_Score": 1.5},
                {"Symbol": "A2", "Antifragility_Score": 1.4},
                {"Symbol": "C0", "Antifragility_Score": 0.1},
                {"Symbol": "C1", "Antifragility_Score": 0.1},
                {"Symbol": "C2", "Antifragility_Score": 0.1},
                {"Symbol": "C3", "Antifragility_Score": 0.1},
                {"Symbol": "C4", "Antifragility_Score": 0.1},
            ]
        )

        optimizer = BarbellOptimizer()

        # Test CRISIS regime (should be defensive)

        portfolio_crisis = optimizer.optimize(returns, stats, regime="CRISIS")

        core_weight = portfolio_crisis[portfolio_crisis["Type"] == "CORE (Safe)"]["Weight"].sum()

        self.assertAlmostEqual(core_weight, 0.97)

        # Test NORMAL regime

        portfolio_normal = optimizer.optimize(returns, stats, regime="NORMAL")

        core_weight_n = portfolio_normal[portfolio_normal["Type"] == "CORE (Safe)"]["Weight"].sum()

        self.assertAlmostEqual(core_weight_n, 0.90)


if __name__ == "__main__":
    unittest.main()
