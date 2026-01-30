"""
Test suite for crypto production infrastructure.
Validates BINANCE-only scanner architecture, hygiene templates, and manifest configuration.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from tradingview_scraper.futures_universe_selector import SelectorConfig, load_config
from tradingview_scraper.settings import get_settings


class TestCryptoHygieneTemplate(unittest.TestCase):
    """Test institutional_crypto.yaml hygiene template."""

    def setUp(self):
        self.hygiene_path = Path("configs/base/hygiene/institutional_crypto.yaml")

    def test_hygiene_template_exists(self):
        """Verify institutional_crypto.yaml exists."""
        self.assertTrue(self.hygiene_path.exists(), "institutional_crypto.yaml should exist")

    def test_hygiene_template_structure(self):
        """Verify hygiene template has required structure."""
        with open(self.hygiene_path) as f:
            config = yaml.safe_load(f)

        # Should extend institutional.yaml
        self.assertIn("base_preset", config)
        self.assertEqual(config["base_preset"], "institutional.yaml")

        # Should have predictability gates
        self.assertIn("predictability", config)
        pred = config["predictability"]
        self.assertEqual(pred["entropy_max"], 0.999)
        self.assertEqual(pred["hurst_min"], 0.40)
        self.assertEqual(pred["hurst_max"], 0.60)
        self.assertEqual(pred["efficiency_min"], 0.15)

        # Should have crypto-specific volume floor
        self.assertIn("volume", config)
        self.assertEqual(config["volume"]["value_traded_min"], 10000000)  # $10M


class TestBinanceMTFScanner(unittest.TestCase):
    """Test binance_mtf_trend.yaml scanner configuration."""

    def setUp(self):
        self.scanner_path = Path("configs/scanners/crypto/binance_mtf_trend.yaml")

    def test_scanner_exists(self):
        """Verify binance_mtf_trend.yaml exists."""
        self.assertTrue(self.scanner_path.exists(), "binance_mtf_trend.yaml should exist")

    def test_scanner_config_loads(self):
        """Verify scanner config loads without errors."""
        config = load_config(str(self.scanner_path))
        self.assertIsInstance(config, SelectorConfig)

    def test_scanner_structure(self):
        """Verify scanner has MTF confirmation screen."""
        with open(self.scanner_path) as f:
            config = yaml.safe_load(f)

        # Should reference binance_perp_top50
        self.assertIn("base_preset", config)
        self.assertIn("binance_perp_top50", config["base_preset"])

        # Should have trend gates
        self.assertIn("trend", config)
        trend = config["trend"]
        self.assertEqual(trend["direction"], "long")
        self.assertEqual(trend["adx"]["min"], 10)

        # Should have MTF confirmation screen
        self.assertIn("confirm_screen", config)
        confirm = config["confirm_screen"]
        self.assertEqual(confirm["timeframe"], "weekly")
        self.assertEqual(confirm["direction"], "long")

        # Should export with correct metadata
        self.assertIn("export_metadata", config)
        meta = config["export_metadata"]
        self.assertEqual(meta["symbol"], "binance_mtf_trend")


class TestCryptoTemplates(unittest.TestCase):
    """Test crypto_perp.yaml and crypto_spot.yaml reference new hygiene."""

    def test_crypto_perp_references_crypto_hygiene(self):
        """Verify crypto_perp.yaml uses institutional_crypto.yaml."""
        perp_path = Path("configs/base/templates/crypto_perp.yaml")
        with open(perp_path) as f:
            config = yaml.safe_load(f)

        self.assertIn("base_preset", config)
        self.assertIn("institutional_crypto", config["base_preset"])

    def test_crypto_spot_references_crypto_hygiene(self):
        """Verify crypto_spot.yaml uses institutional_crypto.yaml."""
        spot_path = Path("configs/base/templates/crypto_spot.yaml")
        with open(spot_path) as f:
            config = yaml.safe_load(f)

        self.assertIn("base_preset", config)
        self.assertIn("institutional_crypto", config["base_preset"])


class TestCryptoProductionManifest(unittest.TestCase):
    """Test crypto_production profile in manifest.json."""

    def setUp(self):
        manifest_path = Path("configs/manifest.json")
        with open(manifest_path) as f:
            self.manifest = json.load(f)

        self.crypto_profile = self.manifest["profiles"]["crypto_production"]

    def test_crypto_production_exists(self):
        """Verify crypto_production profile exists."""
        self.assertIn("crypto_production", self.manifest["profiles"])

    def test_binance_only_scanners(self):
        """Verify scanners are BINANCE-only."""
        scanners = self.crypto_profile["discovery"]["pipelines"]["crypto_alpha"]["scanners"]

        # Should have 5 scanners
        self.assertEqual(len(scanners), 5)

        # Should include new binance_mtf_trend
        self.assertIn("scanners/crypto/binance_mtf_trend", scanners)

        # Should NOT include global_mtf_trend
        global_scanners = [s for s in scanners if "global" in s]
        self.assertEqual(len(global_scanners), 0, "Should not have global scanners")

        # All scanners should be BINANCE-focused
        expected_scanners = {
            "scanners/crypto/binance_trend",
            "scanners/crypto/binance_perp_trend",
            "scanners/crypto/binance_perp_short",
            "scanners/crypto/binance_mtf_trend",
            "scanners/crypto/vol_breakout",
        }
        self.assertEqual(set(scanners), expected_scanners)

    def test_crypto_backtest_parameters(self):
        """Verify crypto-specific backtest parameters."""
        backtest = self.crypto_profile["backtest"]

        # Should have higher slippage
        self.assertEqual(backtest["backtest_slippage"], 0.001)

        # Should have higher commission
        self.assertEqual(backtest["backtest_commission"], 0.0004)

        # Should have crypto benchmarks
        benchmarks = backtest["benchmark_symbols"]
        self.assertIn("BINANCE:BTCUSDT", benchmarks)
        self.assertIn("AMEX:SPY", benchmarks)

    def test_crypto_selection_parameters(self):
        """Verify crypto selection parameters."""
        selection = self.crypto_profile["selection"]

        # Should have broader selection (top 25)
        self.assertEqual(selection["top_n"], 25)

        # Should have relaxed thresholds
        self.assertEqual(selection["threshold"], 0.0)
        self.assertEqual(selection["min_momentum_score"], -1.0)

    def test_crypto_feature_flags(self):
        """Verify crypto feature flags."""
        features = self.crypto_profile["features"]

        # Should use Log-MPS v3.2
        self.assertEqual(features["selection_mode"], "v3.2")

        # Should disable dynamic selection
        self.assertFalse(features["feat_dynamic_selection"])

        # Should enable short direction
        self.assertTrue(features["feat_short_direction"])

        # Should have relaxed entropy threshold
        self.assertEqual(features["entropy_max_threshold"], 0.999)


class TestMakeTargets(unittest.TestCase):
    """Test Make target additions."""

    def test_makefile_has_flow_crypto(self):
        """Verify Makefile has flow-crypto target."""
        makefile_path = Path("Makefile")
        content = makefile_path.read_text()

        self.assertIn("flow-crypto:", content)
        self.assertIn("PROFILE=crypto_production", content)

    def test_makefile_has_crypto_scan_audit(self):
        """Verify Makefile has crypto-scan-audit target."""
        makefile_path = Path("Makefile")
        content = makefile_path.read_text()

        self.assertIn("crypto-scan-audit:", content)


class TestLegacyArchive(unittest.TestCase):
    """Test legacy configs moved to archive."""

    def test_legacy_moved_to_archive(self):
        """Verify configs/legacy moved to configs/archive."""
        legacy_path = Path("configs/legacy")
        archive_path = Path("configs/archive")

        self.assertFalse(legacy_path.exists(), "configs/legacy should not exist")
        self.assertTrue(archive_path.exists(), "configs/archive should exist")


if __name__ == "__main__":
    unittest.main()
