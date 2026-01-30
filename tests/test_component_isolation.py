import unittest
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from tradingview_scraper.utils.technicals import TechnicalRatings


class TestComponentIsolation(unittest.TestCase):
    def setUp(self):
        # Create a simple trend to test indicators
        # 100 periods of rising price
        dates = pd.date_range("2024-01-01", periods=100)
        self.df = pd.DataFrame({"close": np.linspace(100, 200, 100), "high": np.linspace(105, 205, 100), "low": np.linspace(95, 195, 100), "volume": [1000] * 100}, index=dates)

    def test_rsi_calculation(self):
        """Verify RSI output range and trend sensitivity."""
        # pandas-ta RSI
        rsi = ta.rsi(self.df["close"], length=14)
        last_rsi = rsi.iloc[-1]

        # In a perfect uptrend, RSI should be high (> 70)
        self.assertGreater(last_rsi, 70)

        # We can also compare against manual Wilder's smoothing if needed
        # But here we trust pandas-ta's RMA logic for now

    def test_stoch_calculation(self):
        """Verify Stochastic K/D outputs."""
        # Using the tuning from Phase 680 (14, 3, 3)
        stoch = ta.stoch(self.df["high"], self.df["low"], self.df["close"], k=14, d=3, smooth_k=3)
        k = stoch["STOCHk_14_3_3"].iloc[-1]
        d = stoch["STOCHd_14_3_3"].iloc[-1]

        # In uptrend, should be overbought
        self.assertGreater(k, 80)
        self.assertGreater(d, 80)


if __name__ == "__main__":
    unittest.main()
