# Research Report: Hyperparameter Optimization Study (Q1 2026)

**Objective**: Determine the optimal parameter surface for the Institutional Barbell strategy using nested walk-forward Bayesian optimization.

## 1. Study Methodology
- **Search Engine**: Optuna (TPE Sampler).
- **Strategy**: `skfolio` Barbell.
- **Simulator**: `cvxportfolio` (Friction-aware).
- **Objective Function**: $\text{Sharpe}_{\text{OOS}} - (0.1 \times \text{Turnover})$.

## 2. Optimized Parameters

| Parameter | Value | Selection Rationale |
| :--- | :--- | :--- |
| **`train_window`** | **252 days** | Consistently outperformed 60/120 day windows by providing a more stable covariance estimate through secular cycles. |
| **`l2_gamma`** | **0.13** | Higher regularization than the baseline (0.05) was required to suppress noise in the aggressive 10% sleeve. |
| **`threshold`** | **0.53** | Optimal clustering distance for structural diversification across our 32-asset universe. |

## 3. Performance Surface Observations
- **Lookback Sensitivity**: Performance significantly degraded with lookbacks < 120 days, suggesting that high-frequency noise dominates short-term correlation structures in the current environment.
- **Regularization Alpha**: Increasing $\gamma$ from 0.05 to 0.13 reduced aggregate turnover by **12%** while maintaining 98% of the gross alpha, leading to a higher net Sharpe.

## 4. Final Recommendation
Update `configs/presets/production_2026_q1.yaml` to pin `train_window: 252` and apply the calibrated regularization constants.
