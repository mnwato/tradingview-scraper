import unittest

import numpy as np
import pandas as pd

from tradingview_scraper.portfolio_engines import _enforce_cap_series, _project_capped_simplex


class TestCappedSimplexProjection(unittest.TestCase):
    def test_project_capped_simplex_sum_and_bounds(self):
        rng = np.random.default_rng(7)
        raw = rng.normal(loc=0.1, scale=0.5, size=10)
        cap = 0.25

        w = _project_capped_simplex(raw, cap)

        self.assertEqual(len(w), 10)
        self.assertAlmostEqual(float(np.sum(w)), 1.0, places=7)
        self.assertTrue(np.all(w >= -1e-12))
        self.assertTrue(np.all(w <= cap + 1e-9))

    def test_project_capped_simplex_infeasible_cap_is_adjusted(self):
        # With n=3, cap=0.25 is infeasible (3 * 0.25 < 1).
        raw = np.array([0.8, 0.1, 0.1], dtype=float)
        cap = 0.25

        w = _project_capped_simplex(raw, cap)

        self.assertEqual(len(w), 3)
        self.assertAlmostEqual(float(np.sum(w)), 1.0, places=7)
        self.assertTrue(np.all(w >= -1e-12))
        self.assertTrue(np.max(w) <= (1.0 / 3.0) + 1e-6)

    def test_enforce_cap_series_keeps_index(self):
        s = pd.Series([0.9, 0.05, 0.05], index=["a", "b", "c"], dtype=float)
        out = _enforce_cap_series(s, cap=0.4)

        self.assertEqual(list(out.index), ["a", "b", "c"])
        self.assertAlmostEqual(float(out.sum()), 1.0, places=7)
        self.assertTrue((out >= -1e-12).all())
        self.assertTrue((out <= 0.4 + 1e-9).all())


if __name__ == "__main__":
    unittest.main()
