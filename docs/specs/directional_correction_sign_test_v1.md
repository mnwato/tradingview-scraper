# Specification: Directional Correction Sign Test (v1)
**Date:** 2026-01-21  
**Scope:** Crypto + Mixed-direction meta-portfolio sleeves  

## 1. Objective
Certify that SHORT candidate streams are **inverted before ensembling** at the meta boundary, so the meta optimizer consumes **synthetic-long normalized** return streams while the final flattened portfolio preserves true directional intent.

This prevents a mechanical failure mode where the meta layer “punishes” profitable short logic simply because it is anti-correlated with the benchmark.

## 2. Definitions
- **Raw physical returns**: `returns_matrix.parquet` (physical symbols).
- **Synthetic atom returns**: `synthetic_returns.parquet` (atom symbols ending in `_LONG` / `_SHORT`).
- **SHORT inversion rule**:
  - For any atom column `X_*_SHORT`, `synthetic[X_*_SHORT] == -clip(returns_matrix[X], upper=1.0)`.
  - For any atom column `X_*_LONG`, `synthetic[X_*_LONG] == returns_matrix[X]`.

## 3. Requirements
### R3.1 — Inversion Correctness (Hard)
For every synthetic atom column `*_SHORT`:
- the elementwise relation MUST hold:
  - `synthetic == -clip(raw, upper=1.0)` (absolute tolerance `atol=0.0` unless floating conversions require a small epsilon).

**Rationale (Short Risk Isolation)**:
- A short position cannot lose more than 100% of its collateral.
- If a raw asset return exceeds `+100%` in a day (`r > 1.0`), the synthetic short return is capped at `-100%` (`-1.0`).

### R3.2 — Optimizer Normalization (Hard)
In `portfolio_optimized_v2.json` (per risk profile), SHORT atoms MUST appear as normalized LONG positions:
- `Direction == "LONG"`
- `Net_Weight >= 0`

This is the “Synthetic Long Normalization” rule for solvers.

## 4. Audit Tooling
### Script
- `scripts/audit_directional_sign_test.py`

### Usage
Audit a single sleeve run:
```bash
uv run python scripts/audit_directional_sign_test.py --run-id rerun_v3_short_all
```

Audit all sleeves pinned in a meta profile:
```bash
uv run python scripts/audit_directional_sign_test.py --meta-profile meta_crypto_only --risk-profile hrp
```

### Meta Pipeline Gate (Production)
When `features.feat_directional_sign_test_gate=true` for a meta profile, `scripts/run_meta_pipeline.py` runs the sign test as a hard gate before aggregation and persists the results to the meta run directory:
- `data/artifacts/summaries/runs/<RUN_ID>/data/directional_sign_test.json`

Override (tactical):
- `TV_FEATURES__FEAT_DIRECTIONAL_SIGN_TEST_GATE=1` to force-enable
- `TV_FEATURES__FEAT_DIRECTIONAL_SIGN_TEST_GATE=0` to disable (not recommended for production capital workflows)

### Atomic Pipeline Gate (Production)
When `features.feat_directional_sign_test_gate_atomic=true` for an atomic sleeve profile, `scripts/run_production_pipeline.py` runs the sign test as a fail-fast gate:
- after Strategy Synthesis (inversion boundary): `data/directional_sign_test_pre_opt.json`
- after Optimization (adds optimizer normalization sanity): `data/directional_sign_test.json`

Override (tactical):
- `TV_FEATURES__FEAT_DIRECTIONAL_SIGN_TEST_GATE_ATOMIC=1` to force-enable
- `TV_FEATURES__FEAT_DIRECTIONAL_SIGN_TEST_GATE_ATOMIC=0` to disable

## 5. Acceptance Criteria
- **PASS** if there are zero `ERROR` findings.
- Warnings are allowed only for missing optional artifacts (e.g., missing optimizer file), but SHOULD be treated as “not production-ready” for capital workflows.
