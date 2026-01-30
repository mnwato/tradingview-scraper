# Design Specification: Institutional Anomaly Mitigation (v1.0)

## 1. Problem Statement
Forensic audits of Phase 223 identified 337 window-level anomalies, characterized by extreme Sharpe ratios (>10) and unrealistic annualized returns. These occur when solvers (primarily HRP and Max-Sharpe) over-fit to short-term noise or near-zero variance clusters, leading to "bit-perfect" but unstable weights.

## 2. Proposed Architecture

### 2.1 Adaptive Ridge Reloading (CR-690)
- **Mechanism**: The `BacktestEngine` will monitor optimization results in real-time.
- **Trigger**: If a window optimization yields a realized Sharpe > 10.0 (unstable alpha), the engine will automatically re-run the optimization with **Incremental Ridge Loading**.
- **Iteration**:
    1.  Standard Shrinkage (e.g., 0.15).
    2.  If Sharpe > 10: Increase Shrinkage to 0.35.
    3.  If Sharpe > 10: Increase Shrinkage to 0.50 (Max Stability).
- **Goal**: Force diversity in the weight vector by penalizing extreme concentration in noisy factors.

### 2.2 Numerical Stability & Arithmetic Scaling (CR-692)
- **Root Cause**: Geometric annualization of short-term losses (e.g. -17% over 10 days) projects to -99.99% mathematically, creating false anomalies.
- **Fix**: Reporting metrics for windows < 30 days will utilize **Arithmetic Scaling** (`mean_daily_ret * periods`) instead of geometric compounding to prevent projection artifacts.
- **Constraint**: Enforce a **25% Global Weight Cap** per physical asset in all window-level solvers to prevent factor concentration in low-variance clusters.

### 2.3 Integration Path
1.  Update `scripts/backtest_engine.py` to include the `while` loop for adaptive shrinkage.
2.  Update `scripts/optimize_meta_portfolio.py` (if needed) to handle clipped return streams.

## 3. Implementation Plan
1.  **Task 224.1**: Implement `AdaptiveRidge` loop in `BacktestEngine.run_tournament`.
2.  **Task 224.2**: Add `ann_ret` and `sharpe` thresholds to `EngineRequest`.
3.  **Task 224.3**: Verify anomaly count reduction on `binance_spot_rating_all_long`.
