# Plan: Optimization Engine Fidelity

**Track ID**: `optimization_engine_fidelity_20260101`
**Date**: 2026-01-01
**Goal**: Audit and rectify the implementation fidelity of "Risk Parity" and "HRP" profiles across engines (specifically `cvxportfolio`), ensuring they deliver true risk-balanced allocations rather than disguised momentum bets.

## Problem Statement
The "Tournament 4D Audit" revealed that `cvxportfolio`'s "Risk Parity" profile delivered ~59% returns, behaving like a Momentum/MVO strategy. True Risk Parity (ERC) should be lower-volatility and lower-return (closer to `skfolio`'s ~21%). We suspect `CVXPortfolioEngine` is implementing MVO with a risk penalty instead of true ERC.

## Objectives
1.  **CVXPortfolio Audit**: Determine how `risk_parity` is implemented. If it's MVO, fix it or explicitly label it as `mvo_risk_averse`.
2.  **Constraint Verification**: Ensure `cluster_cap` (0.25) is actually applied in the solver.
3.  **Validation Tournament**: Run a final benchmark with `v2` (Stable) and `v3.1` (Alpha) selections across all corrected engines.

## Execution Plan

### Phase 1: Code Audit (Deep Dive)
- [ ] **Step 1**: Read `tradingview_scraper/portfolio_engines/engines.py` and analyze `CVXPortfolioEngine`.
- [ ] **Step 2**: Read `tradingview_scraper/portfolio_engines/base.py` to see how constraints are passed.

### Phase 2: Engine Remediation
- [ ] **Step 3**: If `CVXPortfolio` lacks native ERC, verify if we can approximate it (e.g. `RiskModel` optimization without `ReturnsForecast`?) or if we should fallback to `skfolio`/`custom` for that profile.
- [ ] **Step 4**: "Fix" the implementation or map `risk_parity` to a correct solver.

### Phase 3: Validation Tournament
- [ ] **Step 5**: Run `scripts/run_4d_tournament.py` with:
    -   **Selections**: `v2`, `v3.1`.
    -   **Engines**: `skfolio`, `cvxportfolio`, `custom`.
    -   **Profiles**: `hrp`, `risk_parity`, `benchmark` (EW), `raw_pool_ew`.
- [ ] **Step 6**: Generate comparative report.