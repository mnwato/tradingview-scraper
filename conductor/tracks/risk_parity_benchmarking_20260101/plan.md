# Plan: Risk Parity & HERC Benchmarking

**Track ID**: `risk_parity_benchmarking_20260101`
**Date**: 2026-01-01
**Goal**: Rigorously benchmark and compare various Risk Parity implementations (Native CVX, Custom, Skfolio) and investigate Hierarchical Equal Risk Contribution (HERC) capabilities.

## Problem Statement
We have multiple engines (`cvxportfolio`, `custom`, `skfolio`) offering "Risk Parity" or "HRP". We need to validate that they converge to similar allocations under identical conditions, or understand their divergences. Additionally, we need to clarify if our "HRP" is standard Inverse-Variance HRP or true HERC (Equal Risk Contribution across clusters), and benchmark HERC if available.

## Objectives
1.  **Risk Parity Comparison**:
    *   Benchmark `cvxportfolio` (Native RP) vs `custom` (CVXPY RP) vs `skfolio` (RiskBudgeting).
    *   *Expectation*: All three should yield identical weights for vanilla Risk Parity.
2.  **HRP vs HERC Audit**:
    *   Analyze `custom` HRP implementation. Is it Inverse-Variance (IV) or Equal Risk Contribution (ERC) at the split?
    *   Analyze `skfolio` HRP options.
    *   If HERC is missing, consider implementing it in `custom` as `profile="herc"`.
3.  **Performance Benchmark**:
    *   Run a backtest comparing `risk_parity`, `hrp`, and `herc` (if implemented).

## Execution Plan

### Phase 1: Logic Audit
- [ ] **Step 1**: Review `CustomClusteredEngine`'s HRP implementation.
    *   *Check*: Does it use `1 - var_left / (var_left + var_right)` (IV) or risk contribution?
- [ ] **Step 2**: Review `SkfolioEngine`'s HRP configuration.

### Phase 2: HERC Implementation (if needed)
- [ ] **Step 3**: If `custom` HRP is IV-only, implement `herc` profile in `CustomClusteredEngine` using recursive bisection with ERC allocation at nodes.

### Phase 3: Comparative Benchmark
- [ ] **Step 4**: Create `scripts/benchmark_risk_models.py`.
    *   Inputs: Synthetic covariance with distinct cluster structures.
    *   Outputs: Weights for RP (CVX, Custom, Skfolio), HRP (Custom, Skfolio), HERC (Custom).
    *   Verify weight differences.

### Phase 4: Backtest
- [ ] **Step 5**: Run a "Risk Profile Tournament" using `v3.1` selection.
    *   Profiles: `risk_parity`, `hrp`, `herc`.
