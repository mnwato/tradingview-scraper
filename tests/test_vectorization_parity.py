import unittest
import pandas as pd
import numpy as np
from tradingview_scraper.utils.technicals import TechnicalRatings
from tradingview_scraper.utils.technicals_original import TechnicalRatings as TechnicalRatingsOriginal
import pandas_ta_classic as ta


class TestFeatureVectorizationParity(unittest.TestCase):
    def setUp(self):
        # Create meaningful data
        dates = pd.date_range("2024-01-01", periods=100)
        # Random walk for some variance
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(100))
        high = close + np.abs(np.random.randn(100))
        low = close - np.abs(np.random.randn(100))
        volume = np.abs(np.random.randn(100)) * 1000

        self.df = pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume}, index=dates)

    def test_recommend_ma_parity(self):
        """Verify vectorized Recommend.MA matches original scalar implementation."""
        # Calculate vectorized series
        series_ma = TechnicalRatings.calculate_recommend_ma_series(self.df)
        last_vectorized = float(series_ma.iloc[-1])

        # Calculate original scalar
        last_scalar = TechnicalRatingsOriginal.calculate_recommend_ma(self.df)

        # Original implementation might have slight differences if we changed logic
        # But we aim for equivalence if logic is same
        self.assertAlmostEqual(last_vectorized, last_scalar, places=5)

    def test_recommend_other_parity(self):
        """Verify vectorized Recommend.Other matches original scalar implementation."""
        series_osc = TechnicalRatings.calculate_recommend_other_series(self.df)
        last_vectorized = float(series_osc.iloc[-1])

        last_scalar = TechnicalRatingsOriginal.calculate_recommend_other(self.df)
        self.assertAlmostEqual(last_vectorized, last_scalar, places=5)

    def test_recommend_all_parity(self):
        """Verify vectorized Recommend.All matches original scalar implementation."""
        # Note: We changed the formula for Recommend.All in the new implementation to match docs
        # Old: (buy - sell) / total?? No, let's check old impl.
        # New: 0.574 * MA + 0.3914 * Other (approx avg)

        series_all = TechnicalRatings.calculate_recommend_all_series(self.df)
        last_vectorized = float(series_all.iloc[-1])

        last_scalar = TechnicalRatingsOriginal.calculate_recommend_all(self.df)

        # Check if formula difference is expected
        # If changed, this test might fail, which is informative.
        self.assertAlmostEqual(last_vectorized, last_scalar, places=5)


if __name__ == "__main__":
    unittest.main()
