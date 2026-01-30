# Plan: E2E Workflow & Audit Ledger Integration

## Phase 1: Workflow Review
- [x] **Task**: Audit `FuturesUniverseSelector` for `AuditLedger` integration.
- [x] **Task**: Audit `prepare_portfolio_data.py` for `AuditLedger` integration.
- [x] **Task**: Audit `audit_antifragility.py` for `AuditLedger` integration.
- [x] **Task**: Audit `natural_selection.py` for `AuditLedger` integration.
- [x] **Task**: Audit `optimize_clustered_v2.py` for `AuditLedger` integration.

## Phase 2: Missing Integration
- [x] **Task**: Implement missing `ledger.record_intent()` and `ledger.record_outcome()` calls in identified scripts.
- [x] **Task**: Ensure `run_id` and `profile` are consistently passed to the ledger genesis.

## Phase 3: Verification
- [x] **Task**: Run a full `make daily-run` and verify `artifacts/summaries/runs/<run_id>/audit.jsonl` contains a complete, valid chain.
- [x] **Task**: Verify that re-running a step with the same inputs produces the same hashes (determinism check).
