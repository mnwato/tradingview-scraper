# Specification: Hyperparameter Optimization Standard (Jan 2026)

This document defines the methodology for optimizing the configuration space of the TradingView Scraper quantitative framework.

## 1. Requirements

To prevent "over-optimization bias" (p-hacking), the HPO system must adhere to the following institutional standards:

| Requirement | Implementation | Rationale |
| :--- | :--- | :--- |
| **Temporal Integrity** | Walk-Forward Optimization (WFO) | Prevents look-ahead bias by strictly following chronological order. |
| **Stability Focus** | Surface Smoothing | Prefer parameter regions where performance is stable, not just isolated peaks. |
| **Friction Aware** | Net Sharpe Objective | Optimization objective must subtract transaction costs and slippage. |
| **Complexity Control** | Nested Validation | Use an inner loop for tuning and an outer loop for final performance estimation. |

## 2. Parameter Search Space

| Component | Parameter | Range | Step/Type |
| :--- | :--- | :--- | :--- |
| **Lookback** | `train_window` | 60 - 500 | Discrete [60, 120, 252, 500] |
| **Regularization** | `l2_gamma` | 0.0 - 0.5 | Continuous |
| **Structure** | `threshold` | 0.2 - 0.7 | Continuous (Clustering Distance) |
| **Execution** | `step_size` | 5 - 40 | Discrete [5, 10, 20, 40] |
| **HRP (skfolio)** | `linkage` | single, complete, average, ward | Categorical |
| **HRP (skfolio)** | `risk_measure` | variance, standard_deviation, etc. | Categorical |

## 3. Technical Design

### A. The Objective Function
$$ \text{Objective} = \text{Sharpe}_{\text{out-of-sample}} - \text{Penalty}_{\text{turnover}} $$
The goal is to maximize the net risk-adjusted return across all walk-forward windows. For skfolio HRP, the focus is on **MDD-adjusted Sharpe**.

### B. Implementation: `scripts/research/optimize_skfolio_hrp.py`
Utilize **Optuna** for Bayesian Optimization (TPE Sampler).
1.  **Sampler**: Tree-structured Parzen Estimator (TPE).
2.  **Pruner**: Median Pruner.
3.  **Cross-Validation**: Time-Series Nested CV (5 folds).
4.  **Persistence**: Save study results to `data/lakehouse/optuna_hrp_study.db`.

## 4. Validation & Selection
- **The 1-Sigma Rule**: Choose the simplest (most regularized) parameter set that is within 1 standard deviation of the absolute best peak.
- **Regime Audit**: Verify that the optimized parameters perform consistently across `NORMAL`, `TURBULENT`, and `CRISIS` windows.
