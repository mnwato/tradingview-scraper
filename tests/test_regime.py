import unittest

import pandas as pd

from tradingview_scraper.regime import MarketRegimeDetector


class TestMarketRegimeDetector(unittest.TestCase):
    def test_detect_regime_quiet(self):
        # Setup low-vol, low-noise returns
        # A long series of small, similar returns (low turbulence)
        data = [0.0001, 0.00012, 0.00009, 0.00011] * 20
        returns = pd.DataFrame({"A": data, "B": data})

        detector = MarketRegimeDetector()
        regime, score, quadrant = detector.detect_regime(returns)
        # With very low volatility and noise, it should be QUIET
        self.assertEqual(regime, "QUIET")
        self.assertLess(score, 0.7)

    def test_detect_regime_crisis(self):
        # Setup high-vol spike at the end with a LONG baseline
        # 200 days of low vol
        data = [0.0001, -0.0001] * 100
        returns = pd.DataFrame({"A": data, "B": data})
        # Last 10 are extremely volatile (Shock)
        spike = [0.05, -0.05] * 5
        returns = pd.concat([returns, pd.DataFrame({"A": spike, "B": spike})], ignore_index=True)

        detector = MarketRegimeDetector()
        regime, score, quadrant = detector.detect_regime(returns)
        # Huge vol ratio should trigger CRISIS
        self.assertEqual(regime, "CRISIS")
        self.assertGreaterEqual(score, 1.5)


if __name__ == "__main__":
    unittest.main()
