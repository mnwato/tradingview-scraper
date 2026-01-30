import os
import sys
from unittest.mock import MagicMock, patch

# Ensure imports work for local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.run_production_pipeline import ProductionPipeline  # type: ignore
from tradingview_scraper.settings import get_settings


def test_pipeline_audit_toggle(tmp_path, monkeypatch):
    """Verify that audit ledger is only created if feat_audit_ledger is enabled."""

    # Enable feature flag
    settings = get_settings()
    monkeypatch.setattr(settings, "summaries_dir", tmp_path)

    # 1. Auditing DISABLED
    settings.features.feat_audit_ledger = False

    # Create mock manifest
    manifest_path = tmp_path / "manifest.json"
    with open(manifest_path, "w") as f:
        import json

        json.dump({"profiles": {"test": {}}}, f)

    pipeline_no_audit = ProductionPipeline(profile="test", manifest=str(manifest_path))
    assert pipeline_no_audit.ledger is None

    # 2. Auditing ENABLED
    settings.features.feat_audit_ledger = True

    pipeline_with_audit = ProductionPipeline(profile="test", manifest=str(manifest_path))
    assert pipeline_with_audit.ledger is not None

    audit_file = pipeline_with_audit.run_dir / "audit.jsonl"
    assert audit_file.exists()

    # Verify genesis block was written
    with open(audit_file, "r") as f:
        genesis = json.loads(f.readline())
        assert genesis["type"] == "genesis"

    # Reset flag
    settings.features.feat_audit_ledger = False


def test_pipeline_step_audit_logging(tmp_path, monkeypatch):
    """Verify that pipeline steps record intent and outcome in the ledger."""
    settings = get_settings()
    monkeypatch.setattr(settings, "summaries_dir", tmp_path)
    settings.features.feat_audit_ledger = True

    manifest_path = tmp_path / "manifest.json"

    with open(manifest_path, "w") as f:
        import json

        json.dump({"profiles": {"test": {}}}, f)

    pipeline = ProductionPipeline(profile="test", manifest=str(manifest_path))

    # Mock subprocess.run to succeed
    mock_res = MagicMock()
    mock_res.stdout = "output"
    mock_res.returncode = 0

    with patch("subprocess.run", return_value=mock_res):
        pipeline.run_step("test_step", ["echo", "hello"])

    audit_file = pipeline.run_dir / "audit.jsonl"
    with open(audit_file, "r") as f:
        lines = f.readlines()

    # Line 0: Genesis
    # Line 1: Intent
    # Line 2: Outcome
    assert len(lines) == 3
    intent = json.loads(lines[1])
    outcome = json.loads(lines[2])

    assert intent["step"] == "test_step"
    assert intent["status"] == "intent"
    assert outcome["step"] == "test_step"
    assert outcome["status"] == "success"

    # Reset flag
    settings.features.feat_audit_ledger = False
