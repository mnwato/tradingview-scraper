# Research Report: Quantitative Improvement Plan 2026
**Date**: 2026-01-02
**Status**: Formalized

## 1. Spectral Degeneracy: Root Cause Analysis
An audit of the 2025 Grand Matrix revealed that the **Hard Veto** model for spectral predictability (Entropy > 0.9, Efficiency < 0.1) results in significant alpha leakage. 
- **Finding**: High-momentum assets, particularly in NASDAQ and Crypto, often exhibit high permutation entropy during vertical runs. Discarding these assets based on hard thresholds reduced the annualized selection return from ~30% to ~18%.
- **Conclusion**: Hard vetoes are too blunt for high-volatility alpha capture.

## 2. Proposal: Predictability Soft-Weighting
We propose transitioning from "Pruning" to "Penalty-based Scoring" using the Log-MPS 3.2 framework.

### 2.1 Formula
$Score = \exp\left( \sum \omega_i \ln(P_i) + \ln(1 - \text{Penalty}) \right)$

Where $P_i$ are probabilities derived from:
- **Momentum** (Primary Driver)
- **Survival** (Darwinian Health)
- **Efficiency** (Penalty for Chop)
- **Entropy** (Penalty for Structural Randomness)

### 2.2 Numerical Advantages
- **Continuity**: The scoring surface is continuous, allowing Optuna to identify optimal trade-offs between "Noise" and "Return".
- **Graceful Degradation**: Assets with high entropy are penalized but not discarded if their momentum is high enough to offset the noise penalty.

## 3. Optimizer Stability Guards (skfolio focus)
Audit of `skfolio` vs `custom` engines identified that `skfolio`'s shrinkage-based covariance estimation is significantly more robust against noisy data.

### 3.1 Requirements for Production Optimizers
1. **Kappa Monitor**: Every optimization window MUST log the Condition Number ($\kappa$). If $\kappa > 10^6$, the system should force higher shrinkage or fallback to HRP.
2. **Shrinkage Standard**: Ledoit-Wolf shrinkage is now mandatory for all `min_variance` and `max_sharpe` profiles.
3. **Outlier Filtering**: Optimization results deviating >3σ from the group mean must trigger a "Stability Veto" and fallback to equal weight.

## 4. Strategy Evolution: Higher-Order Moments
Initial evaluation suggests that adding **Skewness** and **Kurtosis** to the component extraction provides better separation for "Antifragile" assets.
- **Skewness**: Positive skew is a primary indicator of "Aggressor" potential in a Barbell strategy.
- **Kurtosis**: High kurtosis (fat tails) combined with positive skew is the target signature for convexity extraction.

## 5. Implementation Roadmap
1. [DONE] Implement component extraction for Higher-Order Moments (Skew/Kurt).
2. [DONE] Implement Log-MPS 3.2 Additive Log-Probability model.
3. [TODO] Perform full HPO study on Skewness weight $\omega_{skew}$.
4. [TODO] Update `skfolio` engine to auto-adjust shrinkage based on $\kappa$.
