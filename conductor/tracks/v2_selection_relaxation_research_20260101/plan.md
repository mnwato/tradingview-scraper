# Research Plan: V2 Selection Relaxation

**Track ID**: `v2_selection_relaxation_research_20260101`
**Date**: 2026-01-01
**Goal**: Investigate if the `v2` universe selection logic is too restrictive, leading to small universes that force portfolio optimizers into concentrated "corner solutions" (e.g., >90% weight in a single asset), despite a 25% `cluster_cap`.

## Context
The "Audit Ledger Integrity" track identified that 25% of non-benchmark optimization windows resulted in a single asset holding >90% weight. Since `cluster_cap` is 0.25, this mathematically implies that the effective universe size passed to the optimizer was likely less than 4 assets (often 1 or 2).

## Objectives
1.  **Quantify Universe Size**: Measure the distribution of the number of assets selected by `v2` logic across the backtest period.
2.  **Analyze Selection Filters**: Identify which filter (Top N, Threshold, Momentum) is the primary bottleneck.
3.  **Propose Relaxation**: Recommend adjusted parameters (e.g., `top_n=5`, `threshold=0.3`) to ensure a minimum viable universe size (e.g., >= 5 assets) for robust optimization.

## Execution Plan

### Phase 1: Analysis
- [x] **Step 1**: Create a diagnostic script `scripts/diagnose_v2_selection.py`.
    -   Run `v2` selection over the backtest period.
    -   Log the number of survivors at each filtering stage (Raw -> Trend -> Momentum -> Final).
    -   Output summary statistics (Mean/Min/Max universe size).
- [x] **Step 2**: Execute the diagnostic script.
    -   **Finding**: The average output universe size is **10.7 assets**, with a minimum of 6.
    -   **Conclusion**: The universe is **NOT** too small. The concentration issue is **NOT** due to restrictive selection. It is a downstream optimizer behavior (likely MVO corner solutions or HRP specific behavior).

### Phase 2: Experimentation
- [ ] **Step 3**: Run experiments with relaxed parameters.
    -   *Cancelled*: Since universe size is healthy (~10), relaxing parameters is not the priority fix for concentration.

### Phase 3: Recommendation
- [ ] **Step 5**: Propose a configuration update.
    -   **Decision**: No changes to `v2` selection logic required. Focus shifts to **Optimization Engine Fidelity** to understand why optimizers concentrate weights despite having ~10 assets available.

## Results
*   **Avg Input Universe**: 32.0
*   **Avg Output Universe**: 10.7
*   **Min Output Size**: 6
*   **Avg Yield Rate**: 33.5%

**Next Step**: Close this track and focus on `optimization_engine_fidelity_20260101`.