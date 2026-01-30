import json
import os

import pytest

from scripts.audit_orchestration import OrchestrationAuditor


@pytest.fixture
def mock_run_structure(tmp_path):
    # Setup a mock run directory structure
    meta_run_id = "meta_run_20260121"
    meta_dir = tmp_path / "runs" / meta_run_id
    meta_dir.mkdir(parents=True)

    # Create manifest
    manifest = {"profiles": {"meta_prod": {"sleeves": [{"id": "s1", "run_id": "s1_run"}, {"id": "s2", "run_id": "s2_run"}]}}}
    (meta_dir / "config").mkdir()
    with open(meta_dir / "config" / "resolved_manifest.json", "w") as f:
        json.dump(manifest, f)

    # Create sleeve directories
    s1_dir = tmp_path / "runs" / "s1_run"
    s1_dir.mkdir(parents=True)

    # s2_dir is missing by default to test failure

    return tmp_path, meta_run_id


def test_detect_missing_sleeve(mock_run_structure):
    base_path, meta_run_id = mock_run_structure
    auditor = OrchestrationAuditor(runs_dir=base_path / "runs")

    report = auditor.audit(meta_run_id)

    assert report["manifest_integrity"]["status"] == "fail"
    assert "s2_run" in report["manifest_integrity"]["errors"][0]


def test_detect_log_errors(mock_run_structure):
    base_path, meta_run_id = mock_run_structure
    meta_dir = base_path / "runs" / meta_run_id

    # Add a log file with an error
    log_file = meta_dir / "execution.log"
    with open(log_file, "w") as f:
        f.write("INFO: Starting\n")
        f.write("ERROR: RayActorError occurred during execution\n")

    auditor = OrchestrationAuditor(runs_dir=base_path / "runs")
    report = auditor.audit(meta_run_id)

    assert report["log_forensics"]["status"] == "fail"
    assert "RayActorError" in report["log_forensics"]["errors"][0]


def test_causality_check(mock_run_structure):
    base_path, meta_run_id = mock_run_structure
    meta_dir = base_path / "runs" / meta_run_id
    s1_dir = base_path / "runs" / "s1_run"

    # Create returns file in sleeve
    (s1_dir / "data" / "returns").mkdir(parents=True)
    s1_rets = s1_dir / "data" / "returns" / "rets_hrp.pkl"
    s1_rets.touch()

    # Create meta returns file
    (meta_dir / "data").mkdir(parents=True)
    meta_rets = meta_dir / "data" / "meta_returns.pkl"
    meta_rets.touch()

    import time

    # Set s1_rets to be NEWER than meta_rets (violation)
    os.utime(meta_rets, (time.time() - 100, time.time() - 100))
    os.utime(s1_rets, (time.time(), time.time()))

    auditor = OrchestrationAuditor(runs_dir=base_path / "runs")
    # We need to manually create s2_dir to pass manifest check
    (base_path / "runs" / "s2_run").mkdir()

    report = auditor.audit(meta_run_id)

    assert report["artifact_parity"]["status"] == "fail"
    assert "newer than meta-matrix" in report["artifact_parity"]["errors"][0]
