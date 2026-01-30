# Specification: Atomic Run Validation (v1)
**Date:** 2026-01-22  
**Scope:** Single-sleeve production runs (“atomic sleeves”) intended for meta-portfolio inclusion  

## 1. Objective
Define a deterministic validation contract for an atomic sleeve run directory.

This spec exists to prevent downstream meta ensembling from consuming sleeves that:
- are missing critical artifacts,
- violate directional correction (SHORT inversion),
- have empty optimizer outputs, or
- are not replayable.

## 2. Contract: Required Artifacts
For an atomic run at:
- `data/artifacts/summaries/runs/<RUN_ID>/`

the following artifacts MUST exist:
- `config/resolved_manifest.json`
- `audit.jsonl`
- `data/returns_matrix.parquet`
- `data/synthetic_returns.parquet`
- `data/portfolio_optimized_v2.json`
- `data/portfolio_flattened.json`

## 3. Directional Sign Test Artifacts (Conditional)
If the executed profile enables the atomic sign-test gate:
- `features.feat_directional_sign_test_gate_atomic=true`

then the run MUST also include:
- `data/directional_sign_test_pre_opt.json` (after synthesis; inversion boundary)
- `data/directional_sign_test.json` (post-optimization; includes optimizer normalization sanity when available)

Both must have `errors == 0`.

## 4. Tooling
### Validator (Hard Gate)
- Script: `scripts/validate_atomic_run.py`
- Output:
  - `reports/validation/atomic_validation_<PROFILE>_<RUN_ID>.md`
  - `reports/validation/atomic_validation_<PROFILE>_<RUN_ID>.json`

Usage:
```bash
uv run python scripts/validate_atomic_run.py --run-id <RUN_ID> --profile <PROFILE>
```

Makefile entrypoint:
```bash
make atomic-validate RUN_ID=<RUN_ID> PROFILE=<PROFILE>
```

### Combined Audit (Sign Test + Validator)
- Script: `scripts/run_atomic_audit.py`
- Output (non-destructive audit artifacts):
  - `data/directional_sign_test_pre_opt_audit.json`
  - `data/directional_sign_test_audit.json`

Usage:
```bash
uv run python scripts/run_atomic_audit.py --run-id <RUN_ID> --profile <PROFILE>
```

Makefile entrypoint:
```bash
make atomic-audit RUN_ID=<RUN_ID> PROFILE=<PROFILE>
```

## 5. Acceptance Criteria
- **PASS** if:
  1) all required artifacts exist, and
  2) `portfolio_optimized_v2.json` contains a non-empty `hrp` asset list, and
  3) `portfolio_flattened.json` contains non-empty weights, and
  4) if the sign gate is enabled, both directional sign-test artifacts exist and have `errors == 0`.

## 6. Rationale
- Atomic sleeves are meta inputs; validation must happen at the sleeve boundary so meta-level failures do not mask root causes.
- Feature-flagging preserves reproducibility while allowing strictness to be increased per profile without global behavior changes.
