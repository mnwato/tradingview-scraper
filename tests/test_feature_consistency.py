import unittest
import pandas as pd
import numpy as np


class TestFeatureConsistency(unittest.TestCase):
    def test_feature_coverage_check(self):
        """Verify that missing symbols are detected in the feature store."""
        returns_symbols = {"BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT"}
        # Missing SOL
        feature_matrix = pd.DataFrame(columns=pd.MultiIndex.from_tuples([("BINANCE:BTCUSDT", "recommend_all"), ("BINANCE:ETHUSDT", "recommend_all")]))

        feature_symbols = set(feature_matrix.columns.get_level_values(0).unique())
        missing = returns_symbols - feature_symbols
        self.assertIn("BINANCE:SOLUSDT", missing)

    def test_nan_ffill_limit(self):
        """Verify that ffill limit for features is respected."""
        s = pd.Series([1.0, np.nan, np.nan, np.nan, np.nan, 2.0])
        # limit=3 should keep the 4th NaN
        filled = s.ffill(limit=3)
        self.assertTrue(np.isnan(filled.iloc[4]))
        self.assertFalse(np.isnan(filled.iloc[1]))


if __name__ == "__main__":
    unittest.main()
