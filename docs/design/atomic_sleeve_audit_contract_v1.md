# Design: Atomic Sleeve Audit Contract (v1)
**Date:** 2026-01-21  
**Scope:** Any single-sleeve production run (atomic sleeve) used as a deterministic input to meta portfolios  

## 1. Objective
Define the minimal artifact contract and audit gates required for an atomic sleeve to be considered **meta-eligible** and **production-auditable**.

Atomic sleeves are the units that meta portfolios ensemble; therefore, failures at the sleeve boundary (missing data, incorrect SHORT inversion, empty optimizer outputs) must be detected before meta aggregation.

## 2. Run Directory Contract
All atomic sleeves MUST write their outputs to:
- `data/artifacts/summaries/runs/<RUN_ID>/`

Minimum required artifacts:
- `config/resolved_manifest.json`  
  Fully resolved runtime configuration snapshot for replayability.
- `audit.jsonl`  
  Forensic decision ledger (genesis + stage intents/outcomes).
- `data/returns_matrix.parquet`  
  Physical-asset daily returns matrix.
- `data/synthetic_returns.parquet`  
  Atom-level returns matrix consumed by direction-naive optimizers.
- `data/portfolio_optimized_v2.json`  
  Optimizer outputs per risk profile (e.g., `hrp`, `min_variance`).
- `data/directional_sign_test.json` (when `feat_directional_sign_test_gate_atomic=true`)  
  Directional correction audit output persisted by the production pipeline.

## 3. Directional Correction Boundary
If a sleeve can produce SHORT atoms, the sleeve MUST satisfy synthetic-long normalization:
- `R_syn_long = R_raw`
- `R_syn_short = -clip(R_raw, upper=1.0)` (short loss cap at -100%)

This boundary is audited using:
- `scripts/audit_directional_sign_test.py`
- `docs/specs/directional_correction_sign_test_v1.md`

## 4. Meta Eligibility (Minimal Gates)
An atomic sleeve is meta-eligible if:
1) required artifacts exist, and  
2) sign test passes (when applicable), and  
3) at least one baseline risk profile output exists and is non-empty (e.g. `hrp`), and  
4) the sleeve is reproducible from `resolved_manifest.json` without manual weight overrides.

## 4.1 Validator (Automation)
Automation reference for enforcing this contract:
- `scripts/validate_atomic_run.py`
- `scripts/run_atomic_audit.py` (runs sign test + validator and writes non-destructive `*_audit.json` artifacts)
- Spec: `docs/specs/atomic_run_validation_v1.md`

## 5. Design Rationale
- **Prevents meta corruption:** meta ensembling amplifies numerical artifacts; strict sleeve contracts localize and bound failure modes.
- **Supports reproducibility:** meta portfolios must be rerunnable from pinned sleeve run ids + manifest snapshots.
- **Separates concerns:** optimizers remain decision-naive; direction and clipping logic is a synthesis-layer responsibility, proven by audit.
