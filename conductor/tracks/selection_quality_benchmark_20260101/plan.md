# Plan: Selection Quality Benchmark

**Track ID**: `selection_quality_benchmark_20260101`
**Date**: 2026-01-01
**Goal**: Quantify the "Alpha" and "Robustness" of the candidate universe produced by the Natural Selection (`v2`/`v3`) logic *before* it reaches the portfolio optimizer.

## Problem Statement
We suspect the `v2` selection logic is too restrictive (`top_n=2`), forcing downstream optimizers into concentrated bets. Before relaxing it, we must benchmark the **quality** of the current selection. Is it selecting the "best" assets, or just the "luckiest"?

## Objectives
1.  **Selection Alpha**: Compare the Equal-Weighted (EW) return of the *Selected Universe* vs the *Raw Discovery Universe*.
    *   *Metric*: `Selection Information Ratio` = (Return_Selected - Return_Raw) / Volatility_Tracking_Error.
2.  **Breadth Analysis**: Measure the "Effective N" (Number of assets) per rebalance window.
    *   *Hypothesis*: If Effective N < 4, `cluster_cap=0.25` is mathematically impossible to enforce without cash drag.
3.  **Win Rate**: What % of selected assets outperform the market benchmark (SPY) in the subsequent test window?

## Execution Plan

### Phase 1: Tooling
- [x] **Step 1**: Create `scripts/benchmark_selection_quality.py`.
    -   Iterate through backtest windows (Train/Test).
    -   Run Selection Logic (`v2` and `v3`).
    -   Calculate `Forward Return` of the *Selected Basket* (EW) vs `Raw Basket` (EW).
    -   Log `N_Selected` per window.

### Phase 2: Analysis
- [x] **Step 2**: Run the benchmark script.
- [x] **Step 3**: Analyze the distribution of `N_Selected`.
- [x] **Step 4**: Calculate the "Hit Ratio" (Probability that a selected asset > Market).

### Phase 3: Decision
- [x] **Step 5**: Determine if we should relax.
    -   **Finding**: The universe size is healthy (~10 assets). The concentration issue is downstream in the optimizer.
- [x] **Step 6**: Audit `cluster_cap` enforcement.
    -   **Finding**: Code review confirms `scripts/backtest_engine.py` and `tradingview_scraper/portfolio_engines/engines.py` correctly propagate and enforce the `cluster_cap` (0.25) via solver constraints or post-projection.

## Results
*   **Selection Alpha**: Positive (0.16% per window).
*   **Universe Size**: Healthy (Avg 10.7 assets).
*   **Constraint Enforcement**: Verified.

**Next Step**: Proceed to **Optimization Engine Fidelity** track to fix why engines are concentrating despite the healthy universe and constraints (likely MVO corner solutions or HRP specific behavior).