import unittest
import pandas as pd
import numpy as np
from tradingview_scraper.utils.technicals import TechnicalRatings


class TestFeatureParity(unittest.TestCase):
    def test_parity_envelope_structure(self):
        """Verify that replicated ratings return sane scalar values."""
        # BTC Dummy Data
        dates = pd.date_range("2024-01-01", periods=500)
        df = pd.DataFrame({"close": np.linspace(50000, 60000, 500), "high": np.linspace(51000, 61000, 500), "low": np.linspace(49000, 59000, 500), "volume": [1000] * 500}, index=dates)

        ma = TechnicalRatings.calculate_recommend_ma(df)
        osc = TechnicalRatings.calculate_recommend_other(df)
        total = TechnicalRatings.calculate_recommend_all(df)

        # Verify range [-1, 1]
        self.assertGreaterEqual(ma, -1.0)
        self.assertLessEqual(ma, 1.0)
        self.assertGreaterEqual(osc, -1.0)
        self.assertLessEqual(osc, 1.0)

        # Total should be weighted average
        expected = (0.574 * ma) + (0.3914 * osc)
        self.assertAlmostEqual(total, expected)


if __name__ == "__main__":
    unittest.main()
