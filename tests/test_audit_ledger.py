import json
import os
import sys

# Ensure imports work for local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.archive.verify_ledger import verify_audit_chain  # type: ignore
from tradingview_scraper.utils.audit import AuditLedger  # type: ignore


def test_audit_ledger_chaining(tmp_path):
    """Test that entries are correctly chained and verifiable."""
    ledger = AuditLedger(tmp_path)

    # Record genesis
    ledger.record_genesis("run-123", "production", "manifest-sha")

    # Record some actions
    ledger.record_intent("step1", {"p": 1}, {"in": "h1"})
    ledger.record_outcome("step1", "success", {"out": "h2"}, {"m": 0.5})

    audit_file = tmp_path / "audit.jsonl"
    assert audit_file.exists()

    # Verify integrity using the production tool
    assert verify_audit_chain(audit_file) is True


def test_audit_ledger_tamper_detection(tmp_path):
    """Test that tampering with the ledger breaks the chain."""
    ledger = AuditLedger(tmp_path)
    ledger.record_genesis("run-123", "production", "manifest-sha")
    ledger.record_intent("step1", {"p": 1}, {"in": "h1"})

    audit_file = tmp_path / "audit.jsonl"

    # Read and tamper
    with open(audit_file, "r") as f:
        lines = f.readlines()

    # Modify a value in the first record (genesis)
    record = json.loads(lines[0])
    record["run_id"] = "TAMPERED"
    lines[0] = json.dumps(record) + "\n"

    with open(audit_file, "w") as f:
        f.writelines(lines)

    # Verification should now fail
    assert verify_audit_chain(audit_file) is False


def test_audit_ledger_resume(tmp_path):
    """Test that ledger can resume from an existing file and maintain the chain."""
    ledger = AuditLedger(tmp_path)
    ledger.record_genesis("run-1", "prod", "h1")
    first_hash = ledger.last_hash

    # Create a new ledger instance pointing to same dir
    ledger2 = AuditLedger(tmp_path)
    assert ledger2.last_hash == first_hash

    ledger2.record_intent("step2", {}, {})
    assert verify_audit_chain(tmp_path / "audit.jsonl") is True
