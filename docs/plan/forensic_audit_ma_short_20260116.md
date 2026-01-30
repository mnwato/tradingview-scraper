# Forensic Audit Plan: `prod_ma_short_v2` Failure (2026-01-16)

## 1. Objective
Investigate the root cause of the poor performance (Sharpe < 0) in the `prod_ma_short_v2` run. Specifically, verify if the issue is due to **Data Quality** (bad prices/signals) or **Strategy Logic** (signal lag/incompatibility).

## 2. Target Run
- **Run ID**: `prod_ma_short_v2`
- **Symptom**: Optimizers (MinVar, MaxSharpe) defaulted to 0% return (cash), while Equal Weight lost money (-8.6% MaxDD).

## 3. Execution Steps

### 3.1 Ledger Analysis
Audit the `audit.jsonl` for `prod_ma_short_v2` to trace decision-making window by window.
- **Check Candidates**: Were valid candidates selected? Or did the selection engine return empty/sparse lists?
- **Check Directions**: Were assets correctly identified as SHORT?
- **Check Optimizers**: Did the optimizers return valid weights, or did they fail to converge (returning zero weights)?

### 3.2 Data Quality Check
Inspect the raw data used for this run.
- **Check Returns Matrix**: `artifacts/summaries/runs/prod_ma_short_v2/data/returns_matrix.parquet`.
    - Are there excessive NaNs?
    - Are the returns for selected assets plausible?
- **Check Selection Audit**: `artifacts/summaries/runs/prod_ma_short_v2/data/selection_audit.json`.
    - Review `Value.Traded` and `Alpha Scores`.

### 3.3 Strategy Logic Review
- **Hypothesis**: The "Moving Average" (MA) rating is too slow for the 10-day rebalancing window (`step_size=10`).
- **Check**: Compare the "MA Rating" signal direction vs. realized 10-day returns. If they are consistently anti-correlated, the strategy is simply wrong for this frequency.

## 4. Deliverable
- A "Forensic Failure Analysis" report detailing the root cause and recommended remediation (Deprecation or Retuning).
