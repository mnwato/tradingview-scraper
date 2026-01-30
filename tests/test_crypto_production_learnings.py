"""
Test suite for crypto production learnings.
Validates staleness logic, barbell split, and calendar alignment.
"""

import json
import unittest
from pathlib import Path
import pandas as pd
import numpy as np


class TestCryptoLearnings(unittest.TestCase):
    """Test empirical learnings from the first crypto production run."""

    def setUp(self):
        self.manifest_path = Path("configs/manifest.json")
        with open(self.manifest_path) as f:
            self.manifest = json.load(f)
        self.crypto_profile = self.manifest["profiles"]["crypto_production"]

    def test_barbell_design_intent(self):
        """Verify barbell split intent (90/10) is codified in risk settings."""
        # Risk profile should be barbell by default or in the profile
        risk_profile = self.manifest["defaults"]["risk"]["profile"]
        self.assertEqual(risk_profile, "barbell", "Default risk profile should be barbell")

        # Check if there are any profile-specific overrides
        if "risk" in self.crypto_profile:
            self.assertEqual(self.crypto_profile["risk"]["profile"], "barbell")

    def test_dual_benchmark_presence(self):
        """Verify both crypto and TradFi benchmarks are present."""
        benchmarks = self.crypto_profile["backtest"]["benchmark_symbols"]
        self.assertIn("BINANCE:BTCUSDT", benchmarks, "Should have crypto benchmark")
        self.assertIn("AMEX:SPY", benchmarks, "Should have TradFi benchmark for cross-asset comparison")

    def test_calendar_intersection_logic(self):
        """Verify the intersection logic for mixed calendars."""
        # Create dummy crypto dates (7 days)
        crypto_dates = pd.date_range(start="2026-01-01", periods=7, freq="D")  # Thu to Wed

        # Create dummy TradFi dates (Weekdays only)
        tradfi_dates = pd.date_range(start="2026-01-01", periods=5, freq="B")  # Thu, Fri, Mon, Tue, Wed

        # Intersection should result in TradFi dates
        intersection = crypto_dates.intersection(tradfi_dates)
        self.assertEqual(len(intersection), 5, "Intersection of Daily and Business should be Business")
        self.assertNotIn(pd.Timestamp("2026-01-03"), intersection)  # Sat
        self.assertNotIn(pd.Timestamp("2026-01-04"), intersection)  # Sun

    def test_staleness_threshold_intent(self):
        """Verify the intent of strict health for stale assets."""
        # Check if strict_health is enabled in the profile or pipeline
        pipeline = self.crypto_profile["discovery"]["pipelines"]["crypto_alpha"]
        self.assertTrue(pipeline["strict_health"], "Strict health must be enabled for production crypto")

    def test_entropy_tolerance(self):
        """Verify crypto entropy tolerance is higher than TradFi."""
        crypto_entropy = self.crypto_profile["features"]["entropy_max_threshold"]
        tradfi_entropy = self.manifest["defaults"]["features"]["entropy_max_threshold"]

        self.assertGreater(crypto_entropy, tradfi_entropy, "Crypto should allow more noise (higher entropy)")
        self.assertEqual(crypto_entropy, 0.999)

    def test_rebalancing_window_optimization(self):
        """Verify the optimized 15-day rebalancing window is codified."""
        step_size = self.crypto_profile["backtest"]["step_size"]
        self.assertEqual(step_size, 15, "Rebalancing window must be 15 days for crypto production")

        test_window = self.crypto_profile["backtest"]["test_window"]
        self.assertEqual(test_window, 30, "Test window must be 30 days for crypto production (2-step lookahead)")


if __name__ == "__main__":
    unittest.main()
