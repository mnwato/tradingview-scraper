# Plan: Barbell Sleeve Diversification & Optimization

## Phase 1: Architecture Review
- [x] **Task**: Analyze `scripts/optimize_clustered_v2.py` to identify points where sleeve-level sub-optimization can be injected.
- [x] **Task**: Define the data interface for passing "Aggressor Candidates" and "Core Candidates" to independent optimizers.

## Phase 2: Implementation
- [x] **Task**: Refactor `run_barbell` to call `_solve_cvxpy_direct` twice: once for the Aggressor sleeve (using `max_sharpe`) and once for the Core sleeve (using `risk_parity`).
- [x] **Task**: Implement a "Global Constraints" wrapper to ensure the combined weights don't breach cluster or sector caps.
- [x] **Task**: Update logic audit in `scripts/validate_portfolio_artifacts.py` to handle multi-asset aggressor clusters.

## Phase 3: Verification
- [x] **Task**: Run a backtest comparison between the "Lead-Asset Barbell" and the "Optimized-Sleeve Barbell".
- [x] **Task**: Verify that the Aggressor sleeve correctly concentrates in high-convexity assets without over-concentrating in a single cluster.
