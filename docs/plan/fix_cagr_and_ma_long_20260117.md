# Remediation Plan: Fix Anomalous CAGR & MA Long Profile (2026-01-17)

## 1. Anomalous CAGR Fix
**Root Cause**: The current reporting engine calculates "Tournament Summary" metrics by **averaging** the annualized metrics of individual 10-day windows.
- Example: 5% return in 10 days $\rightarrow$ Annualized ~500%. Average of 500% is 500%.
- Correct: Total return over 940 days is ~4322%. Annualized (365d) should be $\approx 338\%$.

**Fix Strategy**: Update `scripts/generate_reports.py` to calculate summary metrics from the **Stitched Return Series** (full history) instead of averaging window metrics.

### 1.1 Code Modification (`scripts/generate_reports.py`)
- Modify `_restructure_results_if_needed`:
    - Iterate through the structured `agg` dictionary.
    - For each `sim/eng/prof` node, construct the path to the stitched pickle: `data/returns/{sim}_{eng}_{prof}.pkl`.
    - If pickle exists:
        - Load Series.
        - Calculate `total_return`, `annualized_return`, `sharpe`, `max_drawdown` using `qs`.
        - Overwrite `node["summary"]` with these "Global" metrics.
    - If pickle missing: Fallback to window averaging (legacy behavior).

## 2. Fix `prod_ma_long_v3`
**Status**: Failed due to `AttributeError: dominant_signal` (before the settings fix was applied).
**Action**: Re-run the pipeline for this profile.

## 3. Execution Steps
1.  **Apply Fix**: Edit `scripts/generate_reports.py`.
2.  **Rerun MA Long**: `make flow-production PROFILE=binance_spot_rating_ma_long RUN_ID=prod_ma_long_v3` (Overwrite failed run).
3.  **Regenerate Reports**: Run `make port-report` for the other 3 completed runs to update their `comparison.md` with correct CAGR.
