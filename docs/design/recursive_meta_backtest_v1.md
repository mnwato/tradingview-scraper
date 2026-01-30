# Design: Recursive Meta-Portfolio Backtesting (v1)

## 1. Objective
To enable high-fidelity historical simulation of fractal meta-portfolios where the allocation between sleeves is dynamically re-optimized at each rebalance window.

## 2. Fractal Backtesting Protocol

### 2.1 The Problem
Existing backtests are "Flat": they optimize a single set of assets. Meta-portfolios require a two-tier optimization:
1. **Atomic Tier**: Assets within a sleeve are optimized (e.g., Log-MPS).
2. **Meta Tier**: Sleeves within the meta-portfolio are optimized (e.g., Risk Parity).

### 2.2 Walk-Forward Logic
The `BacktestEngine` will be enhanced to handle recursive rebalancing:

1. **Window $T$**:
   - For each **Sleeve** $S_i$:
     - Run selection/optimization on assets using data up to $T$.
     - Cache the resulting sleeve return stream.
   - For the **Meta-Portfolio**:
     - Aggregate the return streams of all sleeves.
     - Optimize sleeve weights using the aggregated matrix.
   - **Result**: A flattened weight vector for all physical assets at time $T$.

## 3. Architecture Changes

### 3.1 `BacktestEngine` Refactor
Introduce `is_meta_backtest` flag. If true:
- The engine dispatches sub-backtests for each sleeve to generate their walk-forward return streams.
- It then uses the `meta.aggregation` and `risk.optimize_meta` stages to determine the top-level allocation.

### 3.2 Performance Optimization
- **Parallelism**: Sub-backtests will be dispatched via Ray to minimize wall-clock time.
- **Caching**: Results of sub-backtests will be hashed and cached in `data/lakehouse/.cache` to avoid redundant simulation.

## 4. Forensic Reporting
- The meta-report will include **Contribution to Risk** by sleeve.
- Equity curves for each sub-sleeve will be overlaid on the meta equity curve for correlation visualization.

## 5. TDD Strategy
- **`tests/test_recursive_backtest.py`**:
    - Define a meta-profile with two dummy sleeves.
    - Verify that `BacktestEngine` produces a weight matrix containing assets from both sleeves.
    - Verify that sleeve weights vary over time according to the meta-optimizer.
