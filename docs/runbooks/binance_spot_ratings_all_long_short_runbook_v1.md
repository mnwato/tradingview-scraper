# Runbook: Binance Spot Ratings — ALL Long/Short Atomic Pipelines (v1)
**Date:** 2026-01-22  
**Profiles:** `binance_spot_rating_all_long`, `binance_spot_rating_all_short`

## 1. Objective
Run the full atomic production pipelines for the Binance Spot “Rating All” LONG and SHORT sleeves and produce auditable artifacts proving:
- directional correction correctness (SHORT inversion semantics),
- artifact completeness (meta-eligible contract),
- reproducibility via `config/resolved_manifest.json`.

This is the canonical runbook for the baseline directional rating sleeves used in mixed-direction meta portfolios.

## 2. Preconditions
1) Lakehouse inputs are current (scanner exports ingested, returns present, features present if required):
```bash
make flow-data
```
2) Environment is sane:
```bash
make env-check
```

## 3. One-Command Workflow (Recommended)
Runs both atomic sleeves with deterministic run ids and executes post-run audits:
```bash
make flow-binance-spot-rating-all-ls
```

## 4. Manual Workflow (Explicit Run IDs)
Choose explicit run ids for traceability:
- `RUN_LONG=binance_spot_rating_all_long_<YYYYMMDD-HHMMSS>`
- `RUN_SHORT=binance_spot_rating_all_short_<YYYYMMDD-HHMMSS>`

Run the sleeves:
```bash
TV_RUN_ID=$RUN_LONG make flow-production PROFILE=binance_spot_rating_all_long
TV_RUN_ID=$RUN_SHORT make flow-production PROFILE=binance_spot_rating_all_short
```

Audit the sleeves:
```bash
make atomic-audit RUN_ID=$RUN_LONG  PROFILE=binance_spot_rating_all_long
make atomic-audit RUN_ID=$RUN_SHORT PROFILE=binance_spot_rating_all_short
```

## 5. Expected Artifacts
All outputs are written under:
- `data/artifacts/summaries/runs/<RUN_ID>/`

Minimum expected artifacts per run:
- `config/resolved_manifest.json`
- `audit.jsonl`
- `data/returns_matrix.parquet`
- `data/synthetic_returns.parquet`
- `data/portfolio_optimized_v2.json`
- `data/portfolio_flattened.json`

Directional gate artifacts (enabled for these profiles):
- `data/directional_sign_test_pre_opt.json`
- `data/directional_sign_test.json`

Atomic validation outputs:
- `reports/validation/atomic_validation_<PROFILE>_<RUN_ID>.md`
- `reports/validation/atomic_validation_<PROFILE>_<RUN_ID>.json`

## 6. Acceptance Criteria
For each sleeve:
- Directional sign test PASS (`errors == 0`)
- Atomic validation PASS
- Required artifacts exist (contract)

Spec references:
- `docs/specs/binance_spot_ratings_atomic_pipelines_v1.md`
- `docs/specs/atomic_run_validation_v1.md`
- `docs/specs/directional_correction_sign_test_v1.md`
