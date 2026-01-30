"""
Test suite for crypto production configuration validation.
Validates manifest settings, feature flags, and parameter integrity.
"""

import json
import unittest
from pathlib import Path


class TestCryptoConfigValidation(unittest.TestCase):
    """Validate crypto_production profile configuration integrity."""

    def setUp(self):
        self.manifest_path = Path("configs/manifest.json")
        with open(self.manifest_path) as f:
            self.manifest = json.load(f)
        self.crypto_profile = self.manifest["profiles"]["crypto_production"]
        self.defaults = self.manifest["defaults"]

    def test_crypto_profile_exists(self):
        """Verify crypto_production profile is defined."""
        self.assertIn("crypto_production", self.manifest["profiles"])

    def test_selection_parameters(self):
        """Validate selection engine parameters per AGENTS.md crypto standards."""
        selection = self.crypto_profile["selection"]

        # Top N should be 5 for crypto (more volatile universe)
        self.assertEqual(selection["top_n"], 5, "Crypto should select top 5 per cluster")

        # Threshold should be 0.45 (slightly lower than TradFi 0.5)
        self.assertEqual(selection["threshold"], 0.45, "Crypto threshold should be 0.45")

        # Negative momentum floor for SHORT candidates
        self.assertEqual(selection["min_momentum_score"], -0.5)

        # Selection mode should be v3.2 (Log-MPS)
        self.assertEqual(selection["selection_mode"], "v3.2")

    def test_backtest_parameters_crypto_specific(self):
        """Validate crypto-specific backtest settings."""
        backtest = self.crypto_profile["backtest"]

        # Step size must be 20 days (regime alignment per forensic audit)
        self.assertEqual(backtest["step_size"], 20, "Crypto step_size must be 20 days for optimal Sharpe")

        # Train window should be 90 days (crypto cycles faster than TradFi)
        self.assertEqual(backtest["train_window"], 90)

        # Slippage should be 0.1% (higher than TradFi 0.05%)
        self.assertEqual(backtest["backtest_slippage"], 0.001)

        # Commission should be 0.04% (CEX maker/taker fees)
        self.assertEqual(backtest["backtest_commission"], 0.0004)

    def test_dual_benchmark_configuration(self):
        """Verify both crypto and TradFi benchmarks are configured."""
        benchmarks = self.crypto_profile["backtest"]["benchmark_symbols"]

        self.assertIsInstance(benchmarks, list)
        self.assertIn("BINANCE:BTCUSDT", benchmarks, "Must have crypto benchmark")
        self.assertIn("AMEX:SPY", benchmarks, "Must have TradFi cross-asset benchmark")

    def test_feature_flags_crypto(self):
        """Validate crypto-specific feature flags."""
        features = self.crypto_profile["features"]

        # Selection mode must be v3.2
        self.assertEqual(features["selection_mode"], "v3.2")

        # Dynamic selection should be FALSE for stable crypto universe
        self.assertFalse(features["feat_dynamic_selection"], "Crypto benefits from stable universe selection")

        # Short direction must be enabled
        self.assertTrue(features["feat_short_direction"], "Crypto production requires SHORT support")

        # Entropy threshold should be higher (0.999 vs 0.995 TradFi)
        self.assertEqual(features["entropy_max_threshold"], 0.999, "Crypto tolerates higher entropy due to microstructure noise")

        # ECI hurdle should be negative (-0.6) to allow contrarian picks
        self.assertEqual(features["eci_hurdle"], -0.6)

        # Directional returns flag must be enabled
        self.assertTrue(features["feat_directional_returns"])

        # Dynamic direction must be enabled for late-binding
        self.assertTrue(features["feat_dynamic_direction"])

    def test_data_integrity_settings(self):
        """Validate data lookback and health requirements."""
        data = self.crypto_profile["data"]

        # 500 days lookback for secular trends
        self.assertEqual(data["lookback_days"], 500)

        # 90 day floor (alpha immersion floor per CR-114)
        self.assertEqual(data["min_days_floor"], 90, "Crypto floor is 90d to maximize high-momentum participation")

    def test_discovery_crypto_only(self):
        """Verify discovery is BINANCE-only for production."""
        discovery = self.crypto_profile["discovery"]

        # Crypto production should be crypto-only
        self.assertEqual(discovery["enabled_markets"], ["crypto"])

        # Should have crypto_alpha pipeline
        self.assertIn("crypto_alpha", discovery["pipelines"])

        crypto_alpha = discovery["pipelines"]["crypto_alpha"]

        # Validate scanner composition
        scanners = crypto_alpha["scanners"]
        self.assertGreater(len(scanners), 0, "Must have at least one scanner")

        # All scanners should be in crypto namespace
        for scanner in scanners:
            self.assertTrue(scanner.startswith("scanners/crypto/"), f"Crypto production scanner must be crypto-specific: {scanner}")

        # Strict health must be true
        self.assertTrue(crypto_alpha["strict_health"], "Crypto production requires strict_health=true")

    def test_risk_cluster_lookbacks(self):
        """Validate hierarchical cluster lookback windows."""
        risk = self.crypto_profile["risk"]

        # Should have multiple lookback windows including short-term (5d) for crypto
        lookbacks = risk["cluster_lookbacks"]
        self.assertIn(5, lookbacks, "Crypto needs 5d window for fast-moving clusters")
        self.assertIn(60, lookbacks)
        self.assertIn(120, lookbacks)
        self.assertIn(200, lookbacks)

    def test_engines_include_adaptive(self):
        """Verify adaptive meta-engine is included for crypto."""
        engines = self.crypto_profile["backtest"]["engines"]
        self.assertIn("adaptive", engines, "Crypto production should include adaptive meta-engine")


if __name__ == "__main__":
    unittest.main()
