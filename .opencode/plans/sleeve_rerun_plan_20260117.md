# Sleeve Rerun Plan (2026-01-17)

## 1. Objective
Rerun all 4 production sleeves (`long_all`, `short_all`, `long_ma`, `short_ma`) to ensure they generate COMPLETE return streams (all 8 profiles) with the latest codebase. This is a "Correctness Check" before final Meta-Validation.

## 2. Target Profiles (v3)
- `binance_spot_rating_all_long` (ID: `prod_long_all_v3`)
- `binance_spot_rating_all_short` (ID: `prod_short_all_v3`)
- `binance_spot_rating_ma_long` (ID: `prod_ma_long_v3`)
- `binance_spot_rating_ma_short` (ID: `prod_ma_short_v3`)

## 3. Execution Commands
We will use `start-step 11` (Optimization) because the underlying data (Selection/Strategies) has not changed, only the optimization config (adding `barbell`) and engine logic (HRP fix).

```bash
# 1. MA Long
export TV_PROFILE=binance_spot_rating_ma_long 
uv run scripts/run_production_pipeline.py --profile binance_spot_rating_ma_long --manifest configs/manifest.json --run-id prod_ma_long_v3 --start-step 11

# 2. MA Short
export TV_PROFILE=binance_spot_rating_ma_short
uv run scripts/run_production_pipeline.py --profile binance_spot_rating_ma_short --manifest configs/manifest.json --run-id prod_ma_short_v3 --start-step 11

# 3. All Long
export TV_PROFILE=binance_spot_rating_all_long
uv run scripts/run_production_pipeline.py --profile binance_spot_rating_all_long --manifest configs/manifest.json --run-id prod_long_all_v3 --start-step 11

# 4. All Short
export TV_PROFILE=binance_spot_rating_all_short
uv run scripts/run_production_pipeline.py --profile binance_spot_rating_all_short --manifest configs/manifest.json --run-id prod_short_all_v3 --start-step 11
```

## 4. Verification Checklist
For each run directory `artifacts/summaries/runs/<RUN_ID>/data/returns/`, check existence of:
- `custom_cvxportfolio_hrp.pkl`
- `custom_cvxportfolio_min_variance.pkl`
- `custom_cvxportfolio_barbell.pkl`
- `custom_cvxportfolio_max_sharpe.pkl`
- `custom_cvxportfolio_equal_weight.pkl`
- `custom_cvxportfolio_market.pkl`
- `custom_cvxportfolio_benchmark.pkl`
- `custom_cvxportfolio_risk_parity.pkl`

## 5. Updates to Plan
Update `docs/specs/plan.md` to insert this phase as "Phase 218.6: Sleeve Health & Audit (RE-RUN)".
