# Plan: Phase 8 - Bayesian Intelligence & Feedback Loops

**Status**: Active (Planning)
**Date**: 2026-01-01
**Goal**: Transition from purely historical estimation to Bayesian-aware and self-calibrating optimization.

## 1. Task: Black-Litterman Bayesian Estimation
Integrate subjective/regime-based views into the Mu and Sigma estimates.

- **Objective**: Blend the robust Ledoit-Wolf covariance with "Views" derived from the `MarketRegimeDetector`.
- **Implementation**: 
    - Create `tradingview_scraper/portfolio_engines/bayesian.py`.
    - Implement `BlackLittermanEstimator` class.
    - Define a "View Generator" that expresses higher confidence in high-Hurst clusters during `EXPANSION`.
- **Validation**: Compare `black_litterman` profile against static `max_sharpe`.

## 2. Task: Feedback Calibration (The Threshold Auditor)
Develop a learning loop that optimizes the `MarketRegimeDetector` parameters.

- **Objective**: Identify the optimal `crisis_threshold` and `quiet_threshold` based on historical switch success.
- **Action**: Create `scripts/audit_regime_feedback.py`.
- **Logic**: 
    - Replay the `adaptive` profile over the last 17 windows.
    - Calculate "Regime Regret": The difference between the chosen profile and the ex-post best profile for that window.
    - Brute-force/Optimize thresholds to minimize Regret.

## 3. Task: HERC 2.0 (Intra-Cluster Risk Parity)
Refine the hierarchical logic to ensure risk equality at every level of the tree.

- **Objective**: Replace alpha-blended intra-cluster weights with true Inverse-Volatility or ERC weighting *within* each cluster.
- **Rationale**: Current `benchmark` uses HERC for clusters but simple blending for assets. HERC 2.0 ensures the entire structure is risk-balanced.

## 4. Execution Sequence
1.  **HERC 2.0**: Immediate hardening of the hierarchical logic.
2.  **Black-Litterman**: Strategic integration of views.
3.  **Threshold Auditor**: Final loop-closure for adaptive intelligence.
