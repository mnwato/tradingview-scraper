# Plan: Audit Ledger vs Tournament Data Integrity

**Track ID**: `audit_ledger_integrity_20260101`
**Date**: 2026-01-01
**Goal**: Perform a deep-dive audit of the 4D Tournament data (`tournament_4d_results.json`) against the immutable Audit Ledger (`audit.jsonl`). The objective is to verify cryptographic integrity, data consistency, and identify statistical outliers that might indicate simulator or engine drift.

## Context
A recent 4D tournament run (`20260101-215241`) generated both a results JSON and an Audit Ledger. We must ensure these two artifacts tell the exact same story.

## Objectives
1.  **Integrity Check**: Verify that metrics (Sharpe, Volatility, Return) reported in the high-level JSON summary match the granular events recorded in the Audit Ledger.
2.  **Outlier Detection**: Scan the Ledger for:
    *   Extreme weight allocations (e.g., > 90% in one asset when `cluster_cap` is low).
    *   "Ghost" Windows: Windows present in the Ledger but missing from the Results, or vice versa.
    *   Simulator Drift: Significant deviations between `predicted_return` (Optimization step) and `realized_return` (Simulation step) in the ledger.
3.  **Selection Consistency**: Confirm that the Ledger records the correct `selection_mode` metadata for every event.

## Execution Plan

### Phase 1: Exploration & Tooling
- [ ] **Step 1**: Load and inspect the structure of `audit.jsonl` from the latest run.
- [ ] **Step 2**: Create a reconciliation script `scripts/audit_ledger_vs_results.py`.
    -   Inputs: `audit.jsonl`, `tournament_4d_results.json`.
    -   Logic: Match events by `(engine, profile, window_start)`. Compare metrics.
    -   Output: Report discrepancies and statistical outliers.

### Phase 2: Analysis
- [ ] **Step 3**: Run the reconciliation script.
- [ ] **Step 4**: Analyze "Optimization vs Realization" gap (Slippage/Friction analysis) using the Ledger data.

### Phase 3: Reporting
- [ ] **Step 5**: Document findings in `conductor/tracks/audit_ledger_integrity_20260101/report.md`.
- [ ] **Step 6**: If critical issues found, propose fixes.
