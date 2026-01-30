# Specification: Binance Spot Ratings — Atomic Pipelines (v1)
**Date:** 2026-01-21  
**Scope:** Crypto sleeves (BINANCE Spot), rating-based discovery, single-sleeve production runs  

## 1. Objective
Standardize the **full atomic production lifecycle** (Discovery → Selection → Synthesis → Optimization → Reporting → Validation) for the baseline directional sleeves:
- `binance_spot_rating_all_long`
- `binance_spot_rating_all_short`

These sleeves are the canonical baselines for:
1) validating that TradingView “Rating All” signals survive friction, and  
2) proving directional integrity (SHORT inversion) before downstream meta ensembling.

## 2. Profiles & Configuration (Manifest Source of Truth)
Profiles are defined in `configs/manifest.json`:
- `profiles.binance_spot_rating_all_long`
- `profiles.binance_spot_rating_all_short`

### 2.1 Key Profile Invariants (Expected)
**Common:**
- `lookback_days=500`, `min_days_floor=252`
- `top_n=15`, `threshold=0.45`
- `step_size=10` days (crypto regime alignment; updated Jan 2026)
- `benchmark_symbols=["BINANCE:BTCUSDT"]`
- `entropy_max_threshold=0.999`

**Directional:**
- LONG baseline: `features.feat_short_direction=false`
- SHORT baseline: `features.feat_short_direction=true`

## 3. Execution (Atomic Full Pipeline)

Operator runbook:
- `docs/runbooks/binance_spot_ratings_all_long_short_runbook_v1.md`

One-command execution (runs both sleeves + audits):
```bash
make flow-binance-spot-rating-all-ls
```
### 3.1 Commands
Run the full atomic pipeline per profile:
```bash
make flow-production PROFILE=binance_spot_rating_all_long
make flow-production PROFILE=binance_spot_rating_all_short
```

### 3.2 Recommended Immediate Validation (Runbook)
After each run completes, validate directional correctness:
```bash
uv run python scripts/audit_directional_sign_test.py --run-id <RUN_ID>
```

Validate the full atomic sleeve artifact contract:
```bash
uv run python scripts/validate_atomic_run.py --run-id <RUN_ID> --profile binance_spot_rating_all_long
uv run python scripts/validate_atomic_run.py --run-id <RUN_ID> --profile binance_spot_rating_all_short
```

Run the combined audit (sign test + validator):
```bash
make atomic-audit RUN_ID=<RUN_ID> PROFILE=binance_spot_rating_all_short
```

Validation spec reference:
- `docs/specs/atomic_run_validation_v1.md`

### 3.3 Production Gate (Atomic)
These sleeves enable an internal fail-fast sign-test gate via the manifest feature flag:
- `features.feat_directional_sign_test_gate_atomic=true`

When enabled, the production pipeline persists:
- `data/artifacts/summaries/runs/<RUN_ID>/data/directional_sign_test_pre_opt.json` (after synthesis; inversion boundary)
- `data/artifacts/summaries/runs/<RUN_ID>/data/directional_sign_test.json` (post-optimization; includes optimizer normalization sanity when available)
and runs `scripts/validate_atomic_run.py` after Reporting as a fail-fast artifact gate.

If the sleeve is later pinned into a meta profile, validate the meta run after execution:
```bash
uv run python scripts/validate_meta_run.py --run-id <META_RUN_ID> --meta-profile meta_crypto_only
```

### 3.2 Required Outputs (Run Directory)
Each run MUST be reproducible and audit-ready. The run directory is:
- `data/artifacts/summaries/runs/<RUN_ID>/`

Minimum required artifacts for auditability:
- `config/resolved_manifest.json` (replayability)
- `audit.jsonl` (decision ledger)
- `data/returns_matrix.parquet` (raw physical returns)
- `data/synthetic_returns.parquet` (atom-level synthetic returns)
- `data/portfolio_optimized_v2.json` (per-risk-profile outputs)
- `reports/` (human-readable forensic report outputs)

## 4. Directional Integrity (Hard Requirement)
These profiles are baseline directional sleeves; they MUST prove directional correctness at the sleeve boundary:
- LONG atoms: `R_syn_long == R_raw`
- SHORT atoms: `R_syn_short == -clip(R_raw, upper=1.0)` (short loss cap at -100%)

Audit tooling:
- Spec: `docs/specs/directional_correction_sign_test_v1.md`
- Tool: `scripts/audit_directional_sign_test.py`

Run the sign test on the atomic runs:
```bash
uv run python scripts/audit_directional_sign_test.py --run-id <RUN_ID_LONG>
uv run python scripts/audit_directional_sign_test.py --run-id <RUN_ID_SHORT>
```

## 5. Audit Checklist (Atomic Sleeves)
### 5.1 Data / Calendar
- **No padding:** calendar joins MUST NOT introduce zero-filled weekends.
- **Crypto calendar present:** sleeve returns SHOULD include Saturday/Sunday observations.
- **Toxicity guard:** assets with daily returns > 500% (5.0) are dropped; synthetic shorts are capped at -100%.

### 5.2 Selection Health
- **Winner floor:** ensure selection scarcity fallbacks avoid pathological sparsity (target: stable winner set; avoid repeated `N < 3` windows).
- **Liquidity sanity:** Binance Spot sleeves must avoid illiquid microcaps (volume floors are enforced upstream).

### 5.3 Optimization & Outputs
- Confirm expected risk profiles exist in `portfolio_optimized_v2.json` for the primary engine(s).
- Verify weight sum sanity and no NaNs in weight vectors.
- Verify concentration is bounded (cluster caps + physical collapse should not create single-asset dominance).

### 5.4 Performance Sanity (Baseline Expectations)
- LONG sleeve should exhibit positive beta to BTC in raw form.
- SHORT sleeve should exhibit negative beta to BTC in realized (net-weight) form, while its solver-facing synthetic streams remain alpha-aligned.

## 6. Downstream Usage (Meta-Portfolio Inputs)
These atomic sleeves are intended to be pinned as deterministic inputs to meta profiles (e.g. `meta_crypto_only`, `meta_benchmark`).

When used in any meta profile that mixes directions, the meta layer MUST also pass the Directional Correction Sign Test gate.
