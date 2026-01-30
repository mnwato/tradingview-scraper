# Plan: Selection Alpha Benchmark (V2 vs V3 vs Raw)

**Track ID**: `selection_alpha_benchmark_20260101`
**Date**: 2026-01-01
**Goal**: Quantify and compare the "Selection Alpha" of `v2` and `v3` universe selection logic against the **Raw Discovery Universe (Equal-Weight)**.

## Problem Statement
We need to rigorously prove that our "Natural Selection" layer adds value over simply buying the entire eligible universe. The 4D Tournament currently focuses on *optimization* alpha; this track isolates *selection* alpha.

## Objectives
1.  **Metric Definition**:
    *   **Selection Alpha**: `Return(Selected_EW) - Return(Raw_EW)`
    *   **Hit Rate**: % of windows where Selection Alpha > 0.
2.  **Implementation**:
    *   Extend `scripts/backtest_engine.py` (or creating a specialized script) to log `Raw_EW` performance as a baseline profile in the tournament data.
    *   Alternatively, analyze existing `tournament_4d_results.json` if it contains `market` or `benchmark` profiles that proxy for this (unlikely to be exact Raw EW).
3.  **Benchmark**:
    *   Run `v2` Selection.
    *   Run `v3` Selection.
    *   Compare both against `Raw` (No Selection, just liquidity/validity filters).

## Execution Plan

### Phase 1: Tooling Update
- [ ] **Step 1**: Update `scripts/natural_selection.py` or `backtest_engine.py` to support a `raw_pool_ew` "profile" or "engine" that bypasses selection and returns equal weights for all valid candidates.
- [ ] **Step 2**: Ensure `run_4d_tournament.py` includes this new baseline.

### Phase 2: Execution
- [ ] **Step 3**: Run a 4D Tournament including `v2` and `v3` modes, with the new `raw_pool_ew` baseline.

### Phase 3: Reporting
- [ ] **Step 4**: Generate a specific "Selection Alpha Report" table.
    -   Columns: Mode, Win Rate vs Raw, Avg Alpha (bps), Sharpe Delta.

## Artifacts
-   `artifacts/summaries/latest/selection_alpha_report.md`
