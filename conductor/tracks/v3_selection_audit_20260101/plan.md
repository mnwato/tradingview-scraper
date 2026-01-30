# Plan: V3 Selection Pipeline Audit & Improvement

**Track ID**: `v3_selection_audit_20260101`
**Date**: 2026-01-01
**Goal**: Deep-dive audit of the `v3` Natural Selection pipeline to understand its underperformance (-0.31% Alpha vs Raw) and optimize its clustering/pruning logic.

## Problem Statement
The "Selection Alpha Benchmark" showed that `v3` selection actively destroys value compared to a naive Equal-Weight strategy. We need to diagnose *why* (e.g., over-pruning, bad regime detection, poor clustering) and determine the optimal pre-optimization structure (Deduped? Clustered?).

## Objectives
1.  **Code Audit**: Dissect the `v3` logic in `scripts/natural_selection.py`.
2.  **Data Flow Analysis**: Trace `Discovery -> Clustering -> Selection`.
3.  **Benchmarking "Smart Beta" Baselines**:
    *   Compare `v3` not just to "Raw EW", but to "Clustered EW" (Select 1 per cluster randomly or by size) to isolate the value of *Intelligent* selection vs just *Structural* diversification.

## Execution Plan

### Phase 1: Code & Logic Audit
- [x] **Step 1**: Read `scripts/natural_selection.py` and `tradingview_scraper/selection_engines/engines.py`.
- [x] **Step 2**: Document the exact decision tree for `v3`.
    *   **Findings**:
        *   **Clustering**: Used as a *Hard Filter* (Pruning). Selects `top_n` per cluster based on Global Score.
        *   **Panic Mode**: If `kappa > 1e6`, forces `top_n=1`.
        *   **ECI Veto**: Rejects assets where `Alpha - Cost < 2%`.

### Phase 2: Diagnostic Run
- [x] **Step 3**: Create `scripts/diagnose_v3_internals.py`.
    *   **Findings**:
        *   **Permanent Panic**: 94% of windows have `kappa > 1e6`, forcing `top_n=1` per cluster.
        *   **Healthy Width**: Despite panic, avg selected is ~10.3 (due to ~10 clusters).

### Phase 3: Improvement (v3.1)
- [x] **Step 4**: Propose `v3.1` logic updates.
    *   **Fix 1**: Increased `kappa` threshold to `1e18`.
    *   **Fix 2**: Relaxed ECI Veto to 0.5%.
    *   **Verification**: Panic mode eliminated (0/17 windows). Universe size stable at ~11.5.
- [ ] **Step 5**: Benchmark `v3.1`.
    *   Run `benchmark_selection_quality.py` (Need to restore it or add to run_4d_tournament).
    *   Actually, let's use `run_4d_tournament` with `v3.1` mode.