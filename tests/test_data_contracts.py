import unittest
import pandas as pd
import numpy as np
from tradingview_scraper.pipelines.selection.base import IngestionValidator


class TestDataContracts(unittest.TestCase):
    def test_toxicity_bound_validation(self):
        """Verify that assets with > 500% daily returns are flagged as toxic."""
        returns_df = pd.DataFrame(
            {
                "NORMAL_ASSET": [0.01, 0.02, -0.01],
                "TOXIC_ASSET": [0.01, 6.0, -0.01],  # 600% return
            }
        )

        failed = IngestionValidator.validate_returns(returns_df)
        self.assertIn("TOXIC_ASSET", failed)
        self.assertNotIn("NORMAL_ASSET", failed)

    def test_no_padding_compliance(self):
        """Verify that TradFi assets are not zero-padded on weekends."""
        # Mock index with a weekend
        idx = pd.to_datetime(["2024-01-19", "2024-01-20", "2024-01-21", "2024-01-22"])  # Fri, Sat, Sun, Mon

        # TradFi Asset (with :)
        df = pd.DataFrame({"NYSE:AAPL": [0.01, 0.0, 0.0, 0.02]}, index=idx)
        failed = IngestionValidator.validate_returns(df)
        self.assertIn("NYSE:AAPL", failed)

        # Crypto Asset (exempt from padding check in this simple validator)
        df_crypto = pd.DataFrame({"BINANCE:BTCUSDT": [0.01, 0.0, 0.0, 0.02]}, index=idx)
        failed_crypto = IngestionValidator.validate_returns(df_crypto)
        self.assertNotIn("BINANCE:BTCUSDT", failed_crypto)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
