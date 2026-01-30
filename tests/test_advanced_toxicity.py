import unittest
import pandas as pd
import numpy as np
from tradingview_scraper.pipelines.selection.base import AdvancedToxicityValidator


class TestAdvancedToxicity(unittest.TestCase):
    def test_volume_spike_detection(self):
        """Verify Volume Spike detection (> 10 sigma)."""
        # Create 20 days of normal volume (100) and one spike (5000)
        volume = [100.0] * 20 + [5000.0]
        df = pd.DataFrame({"BTC": [0.01] * 21, "volume": volume})

        # μ = 100, σ = 0. So 5000 is infinitely many sigmas away.
        # Even with some variance:
        # μ ≈ 333, σ ≈ 1000? No, let's make it cleaner.

        is_toxic = AdvancedToxicityValidator.is_volume_toxic(df["volume"])
        self.assertTrue(is_toxic)

    def test_price_stall_detection(self):
        """Verify Price Stall detection (> 3 consecutive bars)."""
        # Normal movement then stall
        prices = [100, 101, 102, 102, 102, 102]
        is_stalled = AdvancedToxicityValidator.is_price_stalled(pd.Series(prices))
        self.assertTrue(is_stalled)

        # No stall
        prices_ok = [100, 101, 102, 101, 102, 103]
        is_stalled_ok = AdvancedToxicityValidator.is_price_stalled(pd.Series(prices_ok))
        self.assertFalse(is_stalled_ok)


if __name__ == "__main__":
    unittest.main()
