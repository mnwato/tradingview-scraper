# Spec: Barbell Optimizer Logic Audit

## 1. Problem
The `BARBELL` profile is failing the logic audit with the error:
`❌ LOGIC AUDIT FAILED - Barbell aggressors are not from unique clusters! (2 vs 4)`

This indicates that out of the 4 intended "Aggressor" slots, only 2 unique clusters are represented, violating the diversification mandate of the Barbell strategy.

## 2. Objectives
- Audit the `BarbellEngine` logic in `scripts/optimize_clustered_v2.py`.
- Verify how "Aggressors" are selected from the high-alpha pool.
- Ensure that the cluster-exclusion logic correctly prevents selecting multiple assets from the same risk bucket for the aggressor sleeve.
- Update `scripts/validate_portfolio_artifacts.py` to provide more granular detail on the violation.

## 3. Diversification Mandate
- **Aggressor Sleeve**: Top N high-alpha assets, each MUST belong to a unique cluster.
- **Core Sleeve**: Risk-balanced (HRP/Min-Var) base, excluding assets in the aggressor sleeve.
