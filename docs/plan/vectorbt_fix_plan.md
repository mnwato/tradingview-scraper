# Plan: VectorBT Turnover Fix (Resume)

**Status**: Planned
**Date**: 2025-12-31
**Goal**: Reconcile the `VectorBTSimulator` in the main pipeline with the successful Minimum Viable Reproduction (MVR).

## 1. Findings Recap

- **MVR Success**: `scripts/debug_vectorbt.py` successfully generated trades and calculated turnover using `pf.orders.records_readable` (Turnover ~3.02 for a full flip).
- **Pipeline Failure**: Integrating the exact same logic into `backtest_simulators.py` resulted in `0.00%` turnover in the full tournament report.
- **Hypothesis**: The `pf` object generated in `VectorBTSimulator.simulate` differs from the MVR `pf` object. Specifically:
    - **No Trades Executed**: The `targetpercent` signal might be interpreted as "no change" if the input `weights_df` index doesn't align perfectly with the `prices` index used by `vectorbt`.
    - **Prices Alignment**: The `test_data` passed to `simulate` is sliced from the main returns matrix. If the index isn't perfectly aligned with the `weights_df` (which is constructed from `weights_df` rows), `vectorbt` might skip execution.

## 2. Execution Plan

### Step 1: Deep Inspection in Simulator
Modify `tradingview_scraper/portfolio_engines/backtest_simulators.py` to add temporary debug logging inside the `simulate` method:
1.  **Log Data Shapes**: Print `prices.shape` and `full_weights.shape`.
2.  **Log Index Alignment**: Check `prices.index.equals(full_weights.index)`.
3.  **Log Trade Count**: Explicitly log `len(pf.orders.records_readable)` inside the simulator before calculating metrics.
4.  **Dump Artifacts**: If turnover is 0, dump `prices.head()` and `full_weights.head()` to a JSON/CSV in `artifacts/debug/` for offline inspection.

### Step 2: Signal Alignment Check
In `BacktestEngine`, the `test_data` is `returns.iloc[train_end : train_end + test_window]`.
The `weights_df` comes from the optimizer.
*   **Action**: Ensure `full_weights` in `VectorBTSimulator` is constructed by reindexing `w_series` to `prices.index` using `method='ffill'` (if weights are sparse) or `bfill`. The current implementation uses `np.tile`, which assumes the weights are constant for the *entire* window. This is correct for `FixedWeights` (rebalance once at start), but `vectorbt` might need an initial "buy" signal at t=0.
*   **Fix Idea**: Ensure the *first* timestamp of `full_weights` triggers an entry. `vectorbt` sometimes requires the signal to *change* to trigger. If it starts at 0 and goes to target, it should trade.

### Step 3: VectorBT Configuration
Review `vbt.Portfolio.from_orders` kwargs:
*   `freq="D"`: Might be too strict if data has gaps. Try removing it or using `freq=None`.
*   `cash_sharing=True`: Ensure this is set (MVR used it, pipeline uses default?).
*   `group_by`: MVR used `group_by=True`. Pipeline might need to ensure it's treating the columns as a single portfolio.

## 3. Success Criteria
*   **Log Confirmation**: `backtest_simulators.py` logs show `Order Count > 0`.
*   **Report**: `engine_comparison_report.md` shows non-zero turnover for `vectorbt` rows.
*   **Parity**: Turnover value matches `custom` simulator within 10%.
