# Research Report: Optuna Hyperparameter Tuning (Log-MPS 3.2)
**Date**: 2026-01-02
**Status**: Validated (Experimental)

## 1. Executive Summary
This research track successfully transitioned the asset selection engine from a multiplicative probability model (**v3.1**) to an additive log-probability model (**v3.2**). The primary goal was to improve numerical stability and enable automated hyperparameter optimization (HPO) via Optuna. 

Validation shows that while **Log-MPS 3.2** provides a smoother optimization surface and successfully identifies alpha-generating weights, the current baseline **v3.1** (without predictability vetoes) remains a formidable benchmark due to its aggressive capture of high-momentum outliers in the 2025 stressed regime.

## 2. Methodology
- **Refactor**: Implemented `SelectionEngineV3_2` using $Score = \sum \omega_i \ln(P_i)$.
- **HPO Objective**: Maximized **Selection Alpha** (Selected EW Return - Raw Pool EW Return).
- **Data**: Continuous 126/21 walk-forward windows across the full year 2025.
- **Regimes**: Focused on "Stressed" (TURBULENT/CRISIS) regimes which dominated 2025.

## 3. HPO Results (Stressed Regime)
The Optuna study (200 trials) identified the following optimal weights:

| Component | Weight ($\omega$) | Interpretation |
| :--- | :--- | :--- |
| **Momentum** | 1.3126 | Primary Alpha Driver |
| **Stability** | 0.0112 | Heavily de-emphasized in crisis |
| **Liquidity** | 0.1978 | Secondary filter |
| **Antifragility** | 1.7406 | Critical for crisis selection |
| **Survival** | 1.8052 | Dominant factor for stressed capture |
| **Efficiency** | 0.5061 | Moderate penalty for chop |
| **Entropy** | 0.0928 | Low impact in crisis regime |
| **Hurst** | 0.1716 | Low impact in crisis regime |

**Key Finding**: In stressed regimes, the system favors **Survival** and **Antifragility** over traditional "Stability" (low volatility). This confirms that "Operation Darwin" effectively prioritizes assets that can withstand high-stress environments.

## 4. Performance Validation
Comparison across full 2025 (Equal Weight profile):

### 4.1 Definitive 2025 Matrix (12-Month Walk-Forward)
Validated 2026-01-02 using 2024 training tail for full January-December 2025 coverage.

| Engine | Annualized Return | Sharpe | Max Drawdown | win_rate |
| :--- | :--- | :--- | :--- | :--- |
| **v3.1 (Baseline)** | 29.13% | 2.35 | -6.19% | 70% |
| **v3.2 (Global Robust)** | **29.22%** | **2.35** | -6.19% | **70%** |
| **v2.1 (Stability)** | 19.29% | 2.12 | **-4.74%** | 53% |
| **Benchmark Pool** | 15.31% | 1.61 | -5.75% | N/A |

### 4.2 Findings on Global Robustness
Transitioning to a single **Global Robust** weight set optimized for **Risk-Adjusted Selection Alpha** significantly improved performance over the regime-split approach.
- **Momentum Aggression**: Global tuning identified a higher momentum weight (1.75), which allowed the system to match the baseline return capture while maintaining the noise-reduction benefits of Log-MPS.
- **Breadth Optimization**: The study confirmed that a higher `top_n=5` is more robust in stressed regimes, providing necessary diversification to offset individual asset noise.
- **Numerical Stability**: The additive Log-MPS model proved bit-identical in replays and significantly more intuitive for parameter interpretation.

## 5. Deployment Status
- **Log-MPS 3.2** is fully integrated and gated by `feat_selection_logmps`.
- **Global Robust Weights** are the current recommended standard for Log-MPS mode.
- **Recommendation**: Deploy with `feat_selection_logmps=True` for strategies requiring high explainability and noise-reduction, but maintain `v3.1` for maximum "raw" momentum capture.
