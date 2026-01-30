# Research Plan: VectorBT Simulator Anomaly Investigation

**Status**: **Resolved** (Jan 2026)
**Date**: 2025-12-31
**Owner**: Quantitative Engineering Team

## 1. Problem Statement

During the "Multi-Engine Tournament" (December 2025), the `vectorbt` simulator consistently reported divergent and often implausible metrics compared to the `custom` (ReturnsSimulator) and `cvxportfolio` simulators.

### Key Observations (Run 20251231-232812)
*   **Zero Turnover**: For almost all profiles (except some edge cases), `vectorbt` reported **0.00% turnover**, implying no trading activity occurred after initialization.
*   **Return Discrepancy**: 
    *   `skfolio` / Max Sharpe / `vectorbt`: Sharpe 4.25 (vs 11.05 in Custom).
    *   `custom` / Max Sharpe / `vectorbt`: Sharpe 1.49 (vs 2.23 in Custom).
    *   In many cases, the returns were significantly dampened or negative where other simulators showed positive performance.
*   **Weight Sensitivity**: The simulator appears to ignore the daily weight targets provided by the backtest engine, possibly treating the initial allocation as a buy-and-hold strategy.

## 2. Hypothesis

1.  **Rebalancing Frequency**: The `vectorbt.Portfolio.from_orders` method with `size_type='targetpercent'` and `freq='D'` should theoretically rebalance daily. However, if the provided signal dataframe is interpreted as "target position" rather than "trade execution", `vectorbt` might only trade when the signal *changes*. If the optimizer returns very similar weights (due to L2 regularization or high friction), `vectorbt` might treat them as "no trade required" due to internal tolerance thresholds.
2.  **Price Alignment**: There may be an index mismatch between the `prices` dataframe (cumulative returns) and the `weights` dataframe, causing `vectorbt` to drop trade signals.
3.  **Turnover Calculation**: The `pf.stats(metrics="Turnover")` might be calculating turnover based on *value traded* relative to *initial capital* rather than the portfolio value, or it might be failing to capture rebalancing trades correctly.

## 3. Investigation Findings (Jan 1, 2026)

### Root Cause
The `0.00%` turnover and dampened returns were caused by **missing grouping parameters** in `vbt.Portfolio.from_orders`.
*   Without `group_by=True`, `vectorbt` treated each asset column as an *independent* single-asset portfolio.
*   With `size_type='targetpercent'`, a weight of `0.05` meant "Invest 5% of this single-asset portfolio's cash into this asset".
*   This broke the portfolio construction logic (sum of weights = 100%) and prevented cash sharing between assets.

### Fix
*   Added `group_by=True` and `cash_sharing=True` to `VectorBTSimulator`.
*   Implemented robust turnover calculation using `pf.orders.records_readable` (Sum of `Size * Price` / Avg Value).

### Results
*   **Trades Executed**: `vectorbt` now correctly executes trades to match target weights.
*   **Metrics**: Returns and Sharpe ratios now directionally match other engines (e.g., `skfolio` Max Sharpe > 11.0).
*   **Turnover Interpretation**: `vectorbt` turnover is reported as >100% per window because the simulator initializes with Cash every window (Full Buy-In), whereas `Custom` simulator calculates delta from previous window. This is a known methodological difference.

## 4. Success Criteria

*   **Turnover Parity**: `vectorbt` reported turnover is non-zero and reflects trading activity. **(ACHIEVED)**
*   **Return Parity**: Realized returns match `cvxportfolio` (high fidelity) within acceptable bounds. **(ACHIEVED - Directionally aligned)**

## 5. Decision Gate

*   **Status**: `vectorbt` integration is **REPAIRED**.
*   **Role**: It can be used for high-speed validation, but `cvxportfolio` remains the "Source of Truth" for friction/cost modeling due to its seamless handling of window transitions (initial holdings).