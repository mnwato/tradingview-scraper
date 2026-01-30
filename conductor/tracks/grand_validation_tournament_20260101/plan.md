# Plan: Grand Validation Tournament (Risk & Selection)

**Track ID**: `grand_validation_tournament_20260101`
**Date**: 2026-01-01
**Goal**: Perform a final, comprehensive 4D Tournament to validate the recent improvements in **Selection (v3.1)** and **Optimization (Native RP)**, with a specific focus on comparing Risk Profiles (`risk_parity`, `hrp`, `min_variance`).

## Problem Statement
We have fixed `CVXPortfolioEngine`'s Risk Parity implementation and upgraded Selection to `v3.1`. We validated *Selection Alpha* (return relative to raw), but we haven't rigorously compared the *Risk Profiles* themselves. Does `risk_parity` actually lower volatility compared to `max_sharpe`? Does `hrp` provide better drawdown protection?

## Objectives
1.  **Risk Profile Benchmarking**:
    *   Compare `risk_parity`, `hrp`, `min_variance`, `max_sharpe`.
    *   Metrics: Annualized Volatility, Max Drawdown, Sharpe Ratio.
2.  **Engine Consistency Check**:
    *   Verify `cvxportfolio` vs `custom` vs `skfolio` for *Risk Profiles*.
    *   *Expectation*: `cvxportfolio` and `custom` should be nearly identical for RP. `skfolio` might differ.
3.  **Selection Robustness**:
    *   Confirm `v3.1` (Alpha) vs `v2` (Stable) performance holds across risk profiles.

## Execution Plan

### Phase 1: Tooling
- [ ] **Step 1**: Create `scripts/generate_risk_report.py`.
    *   Reads `tournament_4d_results.json`.
    *   Aggregates results by `Profile` and `Engine`.
    *   Calculates Avg Return, Avg Volatility, Avg Drawdown.
    *   Generates a comparative table (Engine x Profile).

### Phase 2: Tournament Execution
- [ ] **Step 2**: Configure `run_4d_tournament.py` for the Grand Run.
    *   **Selection**: `v2`, `v3.1`.
    *   **Engines**: `custom`, `cvxportfolio`, `skfolio`.
    *   **Profiles**: `risk_parity`, `hrp`, `min_variance`, `max_sharpe`, `benchmark`.
    *   **Simulators**: `custom` (Fastest/Control). (Maybe skip others to save time, or run `cvxportfolio` sim for fidelity). Let's stick to `custom` simulator for pure engine math validation, or `cvxportfolio` if we want realistic costs. Let's use `custom` simulator for speed and direct weight comparison.
- [ ] **Step 3**: Run the tournament.

### Phase 3: Analysis
- [ ] **Step 4**: Run `generate_risk_report.py`.
- [ ] **Step 5**: Run `generate_selection_report.py` (Existing).
- [ ] **Step 6**: Synthesize findings into `report.md`.
