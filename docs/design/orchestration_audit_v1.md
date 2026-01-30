# Design: Orchestration Forensic Audit (Phase 351)

This document specifies the forensic tools required to validate the health and integrity of the new Orchestration Layer (Ray + SDK).

## 1. Objective
Provide a "System Health Check" that audits the execution artifacts of parallel meta-runs to detect silent failures, race conditions, or artifact sync issues.

## 2. Audit Logic (`scripts/audit_orchestration.py`)

The script will accept a `meta_run_id` (or find the latest) and perform the following checks:

### 2.1 Manifest Integrity
- **Check**: Load `manifest.json` from the meta-run.
- **Verify**: Does every `sleeve.id` listed have a corresponding directory in `data/artifacts/summaries/runs/<sleeve_run_id>`?
- **Failure**: Missing directory = Silent Actor Failure.

### 2.2 Log Forensics
- **Check**: Scan `*.log` files in the meta-run and sleeve-runs.
- **Verify**: Absence of `CRITICAL` or unhandled `EXCEPTION` patterns.
- **Verify**: Ray-specific errors (`RayActorError`, `WorkerCrashedError`).

### 2.3 Artifact Parity
- **Check**: Compare `meta_returns.pkl` inputs against sleeve outputs.
- **Verify**: Does the meta-matrix timestamp post-date the sleeve completion? (Causality check).

### 2.4 Performance Anomalies
- **Check**: Analyze `duration` metrics from the audit trail.
- **Verify**: Flag sleeves with <10s runtime (likely crash) or >300% avg duration (stalled).

## 3. TDD Strategy (`tests/test_orchestration_audit.py`)
- **Mock Run Data**: Create a temporary directory structure mimicking a failed meta-run (missing sleeve dir).
- **Assert Detection**: Verify `audit_orchestration` flags the missing sleeve.
- **Mock Logs**: Create a log file with a Ray traceback.
- **Assert Alert**: Verify the auditor catches the traceback.

## 4. Output
- **Console**: Pass/Fail summary.
- **Report**: `orchestration_health.md` in the run directory.
