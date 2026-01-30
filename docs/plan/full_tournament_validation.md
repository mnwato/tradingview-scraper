# Plan: Full Tournament Validation Run

**Status**: Planned
**Date**: 2026-01-01
**Goal**: Execute a comprehensive multi-engine, multi-profile, multi-simulator backtest tournament to validate recent codebase fixes and establish a new performance baseline.

## 1. Scope

- **Engines**:
    - `custom` (L2 Regularized)
    - `market` (Baseline)
    - `skfolio` (Aggressive, L2 Regularized)
    - `riskfolio` (Stable, L2 Regularized)
    - `pyportfolioopt` (Standard MVO)
    - `cvxportfolio` (MPO)

- **Profiles**:
    - `min_variance`
    - `hrp`
    - `max_sharpe`
    - `barbell`
    - `equal_weight`

- **Simulators**:
    - `custom` (Baseline, Delta Turnover)
    - `cvxportfolio` (Friction, Window-Aware)
    - `vectorbt` (Fast, Fresh Buy-In)

## 2. Validation Criteria

1.  **Metric Integrity**:
    - All engines must report non-zero turnover (except possibly `market` hold).
    - `Vol` (Annualized Volatility) column must be populated in the summary report.
    - `vectorbt` turnover should be >100% (reflecting buy-in).

2.  **Engine Stability**:
    - `custom` Max Sharpe should remain < 3.0 (confirming regularization).
    - `skfolio` Max Sharpe > 3.0 (confirming aggressive stance).
    - `cvxportfolio` should generally show lower returns due to friction modeling.

3.  **Error Free**:
    - The run should complete without crashing.
    - Report generation should not fail.
4.  **Data Sufficiency**:
    - Ensure `len(returns.dropna()) >= train_window + test_window` (post-dropna).
    - If short, increase `LOOKBACK` or reduce the window sizes.

## 3. Execution Command

```bash
TV_RUN_ID=<RUN_ID> CLUSTER_CAP=0.25 uv run scripts/backtest_engine.py \
  --tournament \
  --engines custom,market,skfolio,riskfolio,pyportfolioopt,cvxportfolio \
  --profiles min_variance,hrp,max_sharpe,barbell,equal_weight \
  --train 120 \
  --test 20 \
  --step 20 \
  --simulators custom,cvxportfolio,vectorbt
```

## 4. Post-Run Action
- Generate Report: `TV_RUN_ID=<id> uv run scripts/generate_reports.py`
- Analyze `engine_comparison_report.md` for outliers.
- Commit results to `artifacts/summaries`.
- If `tournament_4d_results.json` exists, render the full table:
  `TV_RUN_ID=<id> uv run python scripts/generate_human_table.py`
- For rebalance audit results: `uv run python scripts/generate_human_table.py --rebalance`
