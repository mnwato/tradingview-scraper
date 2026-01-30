# Design: Metrics Reporting V2 (Window-First Aggregation)

## 1. Context & Problem Statement
The current backtesting engine calculates "Annualized Return" and "Sharpe Ratio" for *every* rebalancing window (typically 10-20 days).
- **Issue**: Short-term volatility (e.g., a 40% crash in 10 days) is geometrically annualized to impossible values ($-99.99\%$ or $+1000\%$).
- **Impact**:
    - **Audit Noise**: Forensic logs are flooded with "Bankruptcy" alerts for valid but volatile market events.
    - **Averaging Errors**: Downstream reports that attempt to "average" these window metrics produce garbage results (Mean of [-99%, +5%, +5%] is skewed).
    - **Misleading Signals**: A "Sharpe of 10" in a 10-day window is often just a lucky streak, not alpha.

## 2. Philosophy: Aggregate First, Annualize Second
The new reporting standard shifts the focus from "Projecting every window to a year" to "Measuring the actual period performance".

### 2.1 Window-Level Metrics (The Atomic Unit)
For any window $W_i$ of length $T$ (where $T < 90$ days):
- **Primary Metric**: `Period Return` ($R_W$).
- **Risk Metric**: `Period Volatility` ($\sigma_W$) or `Period Drawdown`.
- **Prohibited**: Do NOT report `Annualized Return` or `Annualized Sharpe` in the primary log view for short windows.

### 2.2 Global Metrics (The Strategy View)
Global performance is derived *only* by stitching the atomic windows together into a continuous equity curve.
1.  **Stitch**: $S_{total} = \text{Concat}(W_1, W_2, ..., W_N)$
2.  **Calculate**: Compute Annualized Return, Sharpe, Sortino, etc., on $S_{total}$.

This ensures that a -40% drop in one window is treated as a -40% drag on the total equity curve, not a -100% bankruptcy event.

## 3. Implementation Plan

### 3.1 `tradingview_scraper/utils/metrics.py` Refactor
- Update `calculate_performance_metrics` to accept a `mode` flag (`'window'` vs `'full'`).
- In `'window'` mode (or auto-detected short `n_obs`):
    - Return `period_return` (raw).
    - Return `period_sharpe` (optional, non-annualized: $\frac{\mu}{\sigma}$).
    - suppress `annualized_*` fields or set them to `None`.

### 3.2 `scripts/backtest_engine.py` Update
- When logging window results to `AuditLedger` or `results` list:
    - Use the new "Period" metrics.
    - Stop calculating/logging `annualized_return` for `test_window` < 60.

### 3.3 Reporting Pipelines
- **`generate_meta_report.py`**: Ensure it consumes `returns/{profile}.pkl` (stitched) rather than averaging `tournament_results.csv` rows.
- **`generate_deep_report.py`**: Update outlier detection to look at `period_return` drops (e.g. < -10%) rather than annualized anomalies.

## 4. Migration Steps
1.  **Refactor Metrics**: Add `period_return` to `calculate_performance_metrics`.
2.  **Update Engine**: Switch `BacktestEngine` to log period metrics.
3.  **Verify**: Re-run a short test (`meta_ray_test`) and verify logs show realistic numbers (e.g. "-14.5%" instead of "-99.99%").
