# Specification: Max Sharpe Institutional Standard (Jan 2026)

This document defines the standardized configuration for the `MAX_SHARPE` risk profile across all supported portfolio optimization engines.

## 1. Requirements

To ensure parity and prevent "Ghost Alpha" (overfitting), all engines must adhere to the following logic:

| Component | Standard | Rationale |
| :--- | :--- | :--- |
| **Risk Measure** | Variance (Standard MVO) | Universal baseline for risk-adjusted returns. |
| **Returns Estimator** | 200-day Annualized Mean | Captures mid-term momentum without being overly sensitive to noise. |
| **Covariance Estimator** | **Ledoit-Wolf Shrinkage** | Reduces eigenvalue spreading and improves out-of-sample stability. |
| **Regularization** | **L2 Ridge (default $\gamma = 0.05$, configurable)** | Penalizes extreme weight concentrations and promotes diversification. |
| **Constraints** | Long-Only, $\sum w = 1$, 25% Cluster Cap | Institutional liquidity and diversification guards. |

**Configurability**: The ridge coefficient is configurable via `EngineRequest.l2_gamma` (default: 0.05). Set `l2_gamma=0.0` to disable explicit L2.

## 2. Technical Design (Updated Jan 2026)

### A. Unified Estimation
We will move covariance estimation out of individual engine wrappers and into the `_optimize_cluster_weights` flow. All engines will be provided with a **Shrunk Covariance Matrix** computed via `sklearn.covariance.ledoit_wolf`.

### B. Wrapper Alignments
- **`custom`**: Uses **Direct Sharpe Maximization** via Charnes-Cooper Transformation with explicit L2 (`l2_gamma`).
- **`skfolio`**: Uses native `MeanRisk(MAXIMIZE_RATIO)` with `l2_coef=l2_gamma`.
- **`riskfolio`**: Uses L2 coefficient `l2_gamma` in classic MVO optimization.
- **`pyportfolioopt`**: Uses `objective_functions.L2_reg(gamma=l2_gamma)` with shrunk covariance.
- **`cvxportfolio`**: Uses `LedoitWolf()` risk forecasting (no explicit ridge term).

## 3. Research Findings: Fractional Programming (Jan 2026)

Implementing direct ratio maximization in the `custom` engine yielded significant improvements:

- **Sharpe Gain**: Realized Sharpe increased from **2.22** to **2.32** (+4.5%).
- **Risk Reduction**: Realized Volatility dropped from **23.6%** to **8.9%**, confirming that direct ratio optimization is more stable out-of-sample than quadratic approximations.
- **Turnover Efficiency**: Average churn reduced by **5%**, as the fractional solver identified more robust optimal weightings.

## 4. Engine Personalities (Audit Findings)

| Archetype | Engine(s) | Strategy | Behavior |
| :--- | :--- | :--- | :--- |
| **Alpha Chaser** | `skfolio` | **Fractional (Ratio) Maximization** | Aggressively concentrates in high-momentum/high-convexity clusters. Chases sectoral alpha. |
| **Risk Smoother** | `cvxportfolio` | **Multi-Period Utility Maximization** | Prioritizes global stability and cost-efficiency. Spreads risk across indices. |
| **Stable Baseline**| `custom`, `riskfolio`, `pyportfolioopt` | **Fractional / Standard Ratio** | Robust defensive posture, favors bond/index hedging. Optimized risk-reward. |

## 5. Next Tasks: Estimation Convergence

Despite mathematical synchronization (Direct Sharpe + L2 + Ledoit-Wolf), `skfolio` still exhibits a unique performance profile (Sharpe > 10). 

**Focus for Feb 2026**:
1. **Estimation Alignment**: Research why `skfolio` internal return/risk estimators identify higher convexity clusters than the standard 200-day mean.
2. **Solver Precision**: Audit if the remaining ~0.3 bps weight difference between solvers impacts the highly non-linear "Max Sharpe" objective in turbulent regimes.
