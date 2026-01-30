import unittest

import numpy as np
import pandas as pd

from tradingview_scraper.portfolio_engines.backtest_simulators import (
    CvxPortfolioSimulator,
    ReturnsSimulator,
    VectorBTSimulator,
)


class TestBacktestSimulators(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(42)
        dates = pd.date_range("2023-01-01", periods=10, tz="UTC")
        self.returns = pd.DataFrame(rng.normal(0.001, 0.01, (10, 3)), index=dates, columns=["A", "B", "C"])  # type: ignore
        self.weights = pd.DataFrame(
            [
                {"Symbol": "A", "Weight": 0.4, "Cluster_ID": "0"},
                {"Symbol": "B", "Weight": 0.3, "Cluster_ID": "1"},
                {"Symbol": "C", "Weight": 0.3, "Cluster_ID": "1"},
            ]
        )

    def test_returns_simulator_basic(self):
        sim = ReturnsSimulator()
        res = sim.simulate(self.returns, self.weights)

        self.assertIn("daily_returns", res)
        self.assertEqual(len(res["daily_returns"]), 10)
        self.assertAlmostEqual(float(res["total_return"]), (1 + res["daily_returns"]).prod() - 1)

    def test_cvx_simulator_available(self):
        sim = CvxPortfolioSimulator()
        if sim.cvp is None:
            self.skipTest("cvxportfolio not installed")

        res = sim.simulate(self.returns, self.weights)
        self.assertIn("daily_returns", res)
        self.assertTrue(len(res["daily_returns"]) >= 9)

    def test_vectorbt_simulator_available(self):
        sim = VectorBTSimulator()
        if sim.vbt is None:
            self.skipTest("vectorbt not installed")

        res = sim.simulate(self.returns, self.weights)
        self.assertIn("daily_returns", res)
        self.assertTrue(len(res["daily_returns"]) >= 8)

    def test_simulator_parity_zero_friction(self):
        # With zero friction, all should be very close
        sim_ret = ReturnsSimulator()
        sim_cvx = CvxPortfolioSimulator()
        sim_vbt = VectorBTSimulator()

        if sim_cvx.cvp is None or sim_vbt.vbt is None:
            self.skipTest("cvxportfolio or vectorbt not installed")

        # Override settings for zero friction
        from unittest.mock import patch

        with patch("tradingview_scraper.portfolio_engines.backtest_simulators.get_settings") as mock_settings:
            mock_settings.return_value.backtest_slippage = 0.0
            mock_settings.return_value.backtest_commission = 0.0
            mock_settings.return_value.backtest_cash_asset = "USDT"

            res_ret = sim_ret.simulate(self.returns, self.weights)
            res_cvx = sim_cvx.simulate(self.returns, self.weights)
            res_vbt = sim_vbt.simulate(self.returns, self.weights)

            # Compare realized vol (more stable than cumulative return for short windows)
            self.assertAlmostEqual(res_ret["realized_vol"], res_cvx["realized_vol"], places=2)
            self.assertAlmostEqual(res_ret["realized_vol"], res_vbt["realized_vol"], places=2)


if __name__ == "__main__":
    unittest.main()
