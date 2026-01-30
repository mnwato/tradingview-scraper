import unittest
import pandas as pd
import numpy as np
import pandera as pa
from tradingview_scraper.pipelines.contracts import ReturnsSchema, WeightsSchema


class TestPanderaContracts(unittest.TestCase):
    def test_returns_contract_validation(self):
        """Verify that malformed returns are rejected with descriptive errors."""
        # Clean data
        df_ok = pd.DataFrame({"BTC": [0.01, -0.02, 0.03]}, index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))

        ReturnsSchema.validate(df_ok)

        # Toxic data (> 100% daily)
        df_toxic = pd.DataFrame({"BTC": [0.01, 6.0, 0.03]}, index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))

        with self.assertRaises(pa.errors.SchemaError):
            ReturnsSchema.validate(df_toxic)

    def test_weights_sum_contract(self):
        """Verify that WeightsSchema detects weight leakage."""
        df_leak = pd.DataFrame(
            {
                "Symbol": ["A", "B"],
                "Weight": [0.6, 0.6],  # Sum = 1.2
            }
        )

        with self.assertRaises(pa.errors.SchemaError):
            WeightsSchema.validate(df_leak)


if __name__ == "__main__":
    unittest.main()
