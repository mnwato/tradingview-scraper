# Design: Meta-Portfolio Backtest Benchmarking (v1)

## 1. Objective
To benchmark the performance of the recursive meta-portfolio backtest against static and simple-weighted baselines, ensuring the recursive rebalancing adds value and maintains numerical stability.

## 2. Benchmarking Protocol

### 2.1 Baselines
1. **Equal-Weight Meta (EWM)**: Every sleeve is assigned a static $1/N$ weight.
2. **Static HRP Meta**: Sleeves are weighted using HRP based on the full historical period (lookahead bias baseline).
3. **Recursive HRP Meta (Production)**: Sleeves are dynamically re-weighted at each window using trailing returns.

### 2.2 Metrics
- **Portfolio Sharpe Ratio**: Primary risk-adjusted return metric.
- **Turnover (Churn)**: Measure of how much the sleeve allocations change between windows.
- **Allocation Stability**: Standard deviation of sleeve weights over time.
- **Max Drawdown**: Tail-risk comparison.

## 3. Implementation Details

### 3.1 `BacktestEngine` Output
The engine must output a `meta_backtest_results.json` containing:
- Time-series of sleeve weights.
- Stitched equity curve for each baseline.
- Comparative statistics table.

### 3.2 Report Integration
Update `generate_meta_report.py` to:
- Plot the "Meta-Equity Curve" (Recursive vs. Equal Weight).
- Plot "Sleeve Allocation Over Time" (Stacked Area Chart).

## 4. TDD Strategy
- **`tests/test_meta_backtest_benchmarking.py`**:
    - Mock a 3-window meta-backtest.
    - Verify that the weight of Sleeve A changes between Window 1 and Window 2.
    - Verify that the final equity curve is the product of these dynamic weights.

## 5. Execution Strategy
Use `make port-test PROFILE=meta_benchmark` to trigger the recursive engine.
