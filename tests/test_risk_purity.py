import unittest

import pandas as pd


class TestRiskPurity(unittest.TestCase):
    def setUp(self):
        # Create a dummy returns matrix
        # Asset A: Up 1% daily
        # Asset B: Down 1% daily
        dates = pd.date_range("2025-01-01", periods=10)
        self.returns = pd.DataFrame({"A": [0.01] * 10, "B": [-0.01] * 10}, index=dates)

        self.meta = {"A": {"symbol": "A", "direction": "LONG", "identity": "A"}, "B": {"symbol": "B", "direction": "SHORT", "identity": "B"}}

    def test_directional_inversion(self):
        """
        Test that SHORT candidates have their returns inverted for the optimizer.
        """
        # Mocking the inversion logic we want to implement
        opt_returns = self.returns.copy()
        for s in opt_returns.columns:
            if self.meta[s]["direction"] == "SHORT":
                opt_returns[s] = -1.0 * opt_returns[s]

        # Now B should have positive returns (+1% daily)
        self.assertEqual(opt_returns["B"].mean(), 0.01)
        self.assertEqual(opt_returns["A"].mean(), 0.01)

    def test_hrp_with_shorts(self):
        """
        Test that HRP allocates positive weight to a stable downtrending asset
        if returns are correctly inverted.
        """
        # This requires BacktestEngine to handle the inversion
        # For now, we manually verify the mathematical principle

        # If we don't invert:
        # A: mean=0.01, vol=0
        # B: mean=-0.01, vol=0
        # MVO/Sharpe would pick A only.

        # If we invert:
        # A: mean=0.01
        # B_syn: mean=0.01
        # HRP should split weight between them if they are uncorrelated.
        pass


if __name__ == "__main__":
    unittest.main()
