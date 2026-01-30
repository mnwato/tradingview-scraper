# Audit Plan: Binance Spot Ratings — Atomic Sleeves (v1)
**Date:** 2026-01-21  
**Profiles:** `binance_spot_rating_all_long`, `binance_spot_rating_all_short`  

## 1. Objective
Provide a deterministic, repeatable audit plan for the two baseline directional Binance Spot rating sleeves. These runs serve as the “atoms” that validate:
- data integrity + calendar correctness (crypto 24x7),
- selection stability (winner floors),
- directional correction correctness (SHORT inversion),
- solver output sanity and flattening integrity.

## 2. Execution (Run the Atomic Sleeves)
```bash
make flow-production PROFILE=binance_spot_rating_all_long
make flow-production PROFILE=binance_spot_rating_all_short
```

One-command workflow (runs both sleeves + audits):
```bash
make flow-binance-spot-rating-all-ls
```

Operator runbook:
- `docs/runbooks/binance_spot_ratings_all_long_short_runbook_v1.md`

Record the resulting run ids from:
- `data/artifacts/summaries/runs/`

## 3. Required Artifacts (Per Run)
For each `<RUN_ID>` under `data/artifacts/summaries/runs/<RUN_ID>/`:
- [ ] `config/resolved_manifest.json`
- [ ] `audit.jsonl`
- [ ] `data/returns_matrix.parquet`
- [ ] `data/synthetic_returns.parquet`
- [ ] `data/portfolio_optimized_v2.json`

## 4. Directional Correction Audit (Hard Gate)
Run the sign test:
```bash
uv run python scripts/audit_directional_sign_test.py --run-id <RUN_ID>
```

Acceptance:
- PASS if zero `ERROR` findings.
- For SHORT streams, inversion is validated as `synthetic_SHORT == -clip(raw, upper=1.0)` (short loss cap).

If the atomic sign-test gate is enabled (`feat_directional_sign_test_gate_atomic=true`), the run directory SHOULD already contain:
- `data/directional_sign_test_pre_opt.json`
- `data/directional_sign_test.json`

Optional combined audit command:
```bash
make atomic-audit RUN_ID=<RUN_ID> PROFILE=<PROFILE>
```

## 5. Sleeve Health + Data Integrity
Minimum checks:
- [ ] **Missing bars:** veto any sleeve with missing daily bars under strict health workflows.
- [ ] **Crypto weekend presence:** confirm Saturdays/Sundays exist in the time index.
- [ ] **No zero-fill:** ensure no “flatlined” weekends are introduced by padding.
- [ ] **Toxicity guard:** confirm any daily `> 500%` raw moves are excluded; synthetic short cap is enforced.

## 6. Risk Output Sanity (Per Risk Profile)
From `data/portfolio_optimized_v2.json`:
- [ ] The expected risk profile(s) exist (at least `hrp` for production baselines).
- [ ] Weight vectors have no NaNs/inf.
- [ ] Weights sum is stable and non-zero (`W_sum > 1e-6`).

## 7. Report & Certification Outputs
- [ ] A human-readable report exists in `reports/` and includes top holdings + key performance stats.
- [ ] The run can be replayed from `config/resolved_manifest.json` without manual overrides.
- [ ] Atomic validator PASS:
```bash
uv run python scripts/validate_atomic_run.py --run-id <RUN_ID> --profile <PROFILE>
```

## 8. Downstream Meta Readiness
These atomic sleeves are eligible meta inputs only if:
- Directional sign test PASS
- Artifacts present
- Solver outputs are non-empty for the baseline risk profile(s)

Reference spec:
- `docs/specs/binance_spot_ratings_atomic_pipelines_v1.md`
- `docs/specs/atomic_run_validation_v1.md`
