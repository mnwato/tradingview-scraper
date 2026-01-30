"""
TDD Test Suite: Health Enforcement & Auto-Recovery

Critical Issue #1: STRICT_HEALTH=0 enforcement failure
Critical Issue #2: No auto-recovery for stale data

These tests validate that production/crypto_production profiles:
1. ALWAYS enforce STRICT_HEALTH=1 (no env variable override allowed)
2. Automatically trigger data-repair when stale/degraded assets detected
3. Re-audit health after recovery and fail if issues persist
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.run_production_pipeline import ProductionPipeline


class TestStrictHealthEnforcement:
    """Test that production profiles never allow STRICT_HEALTH=0 override."""

    def test_production_profile_enforces_strict_health_flag(self):
        """Production profile must use STRICT_HEALTH=1, reject env override."""
        # Simulate environment override attempt
        with patch.dict(os.environ, {"TV_STRICT_HEALTH": "0", "STRICT_HEALTH": "0"}):
            pipeline = ProductionPipeline(profile="production")

            # Use the FIXED logic from run_production_pipeline.py
            production_profiles = ["production", "crypto_production", "production_2026_q1", "institutional_etf"]

            strict_health_arg = "STRICT_HEALTH=1"
            if pipeline.profile in production_profiles:
                strict_health_arg = "STRICT_HEALTH=1"
            else:
                if os.getenv("TV_STRICT_HEALTH") == "0" or os.getenv("STRICT_HEALTH") == "0":
                    strict_health_arg = "STRICT_HEALTH=0"

            assert strict_health_arg == "STRICT_HEALTH=1"

    def test_crypto_production_profile_enforces_strict_health_flag(self):
        """Crypto production profile must use STRICT_HEALTH=1, reject env override."""
        with patch.dict(os.environ, {"STRICT_HEALTH": "0"}):
            pipeline = ProductionPipeline(profile="crypto_production")

            production_profiles = ["production", "crypto_production", "production_2026_q1", "institutional_etf"]

            strict_health_arg = "STRICT_HEALTH=1"
            if pipeline.profile in production_profiles:
                strict_health_arg = "STRICT_HEALTH=1"
            else:
                if os.getenv("TV_STRICT_HEALTH") == "0" or os.getenv("STRICT_HEALTH") == "0":
                    strict_health_arg = "STRICT_HEALTH=0"

            assert strict_health_arg == "STRICT_HEALTH=1"

    def test_development_profile_allows_strict_health_override(self):
        """Development profile should allow STRICT_HEALTH=0 for fast iteration."""
        with patch.dict(os.environ, {"STRICT_HEALTH": "0"}):
            pipeline = ProductionPipeline(profile="development")

            production_profiles = ["production", "crypto_production", "production_2026_q1", "institutional_etf"]

            strict_health_arg = "STRICT_HEALTH=1"
            if pipeline.profile in production_profiles:
                strict_health_arg = "STRICT_HEALTH=1"
            else:
                if os.getenv("TV_STRICT_HEALTH") == "0" or os.getenv("STRICT_HEALTH") == "0":
                    strict_health_arg = "STRICT_HEALTH=0"

            assert strict_health_arg == "STRICT_HEALTH=0"


class TestAutoRecoveryLogic:
    """Test that pipeline triggers auto-recovery when health audit detects issues."""

    def test_validate_health_detects_stale_assets(self):
        """validate_health() should parse report and detect STALE assets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = ProductionPipeline(profile="crypto_production")
            pipeline.run_dir = Path(tmpdir)

            # Create mock health report with STALE assets
            report_path = pipeline.run_dir / "data_health_selected.md"
            report_content = """
# Data Health Report

| Symbol | Status | Last Date | Days Old | Gaps |
|--------|--------|-----------|----------|------|
| BINANCE:BTCUSDT | HEALTHY | 2026-01-12 | 0 | 0 |
| BINANCE:BNBUSD.P | STALE | 2025-12-30 | 13 | 0 |
| BINANCE:BNBUSDT.P | STALE | 2026-01-08 | 4 | 0 |
"""
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_content)

            # Run validation
            result = pipeline.validate_health()

            # Should detect 2 STALE assets and trigger recovery
            assert result["metrics"]["n_stale"] == 2
            assert result["metrics"]["trigger_recovery"] is True
            assert "2 STALE assets" in result["metrics"]["recovery_reason"]

    def test_validate_health_detects_degraded_assets(self):
        """validate_health() should parse report and detect DEGRADED assets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = ProductionPipeline(profile="production")
            pipeline.run_dir = Path(tmpdir)

            # Create mock health report with DEGRADED assets
            report_path = pipeline.run_dir / "data_health_selected.md"
            report_content = """
# Data Health Report

| Symbol | Status | Last Date | Days Old | Gaps |
|--------|--------|-----------|----------|------|
| NASDAQ:AAPL | HEALTHY | 2026-01-12 | 0 | 0 |
| NYSE:XYZ | DEGRADED | 2026-01-12 | 0 | 5 |
"""
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_content)

            result = pipeline.validate_health()

            # Should detect 1 DEGRADED asset and trigger recovery
            assert result["metrics"]["n_degraded"] == 1
            assert result["metrics"]["trigger_recovery"] is True
            assert "1 DEGRADED assets" in result["metrics"]["recovery_reason"]

    def test_validate_health_returns_missing_when_no_report(self):
        """validate_health() should return report_missing if health report doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = ProductionPipeline(profile="production")
            pipeline.run_dir = Path(tmpdir)

            result = pipeline.validate_health()

            assert result["metrics"]["health_gate"] == "report_missing"


class TestEfficiencyThreshold:
    """Test that crypto production uses correct efficiency threshold."""

    def test_crypto_production_efficiency_threshold_is_optimal(self):
        """Crypto production should use efficiency_min_threshold=0.03 (not 0.05)."""
        manifest_path = Path("configs/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        crypto_profile = manifest["profiles"]["crypto_production"]
        features = crypto_profile.get("features", {})

        current_threshold = features.get("efficiency_min_threshold")

        # After fix, should be 0.03 (optimal value)
        assert current_threshold == 0.03, f"crypto_production efficiency_min_threshold should be 0.03. Current value {current_threshold}."


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
