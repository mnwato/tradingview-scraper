# Plan: CVXPortfolio Risk Parity & HRP Implementation

**Track ID**: `cvxportfolio_risk_implementation_20260101`
**Date**: 2026-01-01
**Goal**: Attempt to implement true "Risk Parity" (ERC) and "Hierarchical Risk Parity" (HRP) natively within the `CVXPortfolio` ecosystem, and rigorously audit the existing `Custom` implementations.

## Problem Statement
Currently, `CVXPortfolioEngine` falls back to the `Custom` engine for `risk_parity` and `hrp` profiles because standard `cvxportfolio` objectives (ReturnsForecast, FullCovariance) define Mean-Variance problems. However, `cvxportfolio` supports symbolic custom objectives. We should explore if we can implement the canonical Risk Parity log-barrier formulation (`maximize sum(log(w)) - 0.5 * w'Σw`) using `cvxportfolio` primitives.

Additionally, we need to verify the correctness of the `Custom` engine's `scipy`-based HRP and `cvxpy`-based Risk Parity to ensure our "fallback" is actually robust.

## Objectives
1.  **Audit Custom HRP/RP**: Verify the logic in `_get_recursive_bisection_weights` and `_solve_cvxpy(profile="risk_parity")`.
2.  **Native CVXPortfolio Risk Parity**: Attempt to define a `cvx.Maximize(cvx.Sum(cvx.Log(w)) ...)` objective passed to `cvx.SinglePeriodOptimization`.
3.  **Native CVXPortfolio HRP**: Determine if HRP (an algorithmic approach) can or should be integrated into `cvxportfolio` (which is a convex solver wrapper). *Hypothesis: No, HRP is an algorithm, not a convex problem.*

## Execution Plan

### Phase 1: Custom Engine Audit
- [ ] **Step 1**: Review `tradingview_scraper/portfolio_engines/engines.py` for `CustomClusteredEngine`.
    *   Check HRP recursive bisection logic (Lopez de Prado standard).
    *   Check Risk Parity Log-Barrier formulation (`0.5 x'Sx - sum(log(x))`).

### Phase 2: CVXPortfolio Prototyping
- [ ] **Step 2**: Create a prototype script `scripts/prototype_cvx_rp.py`.
    *   Load sample covariance.
    *   Try to construct `cvxportfolio` objective for Risk Parity.
    *   Run `cvx.SinglePeriodOptimization`.
- [ ] **Step 3**: If successful, integrate into `CVXPortfolioEngine`.

### Phase 3: Validation
- [ ] **Step 4**: Run a benchmark comparing `Custom` RP vs `CVXPortfolio` RP (if implemented). They should yield identical weights.
