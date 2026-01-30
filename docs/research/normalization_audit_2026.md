# Research Report: Normalization Sensitivity Audit (Selection v2.1)
**Date**: 2026-01-02
**Status**: Formalized Standard

## Executive Summary
This audit investigated the impact of transition from **uniform ranking** to **magnitude-preserving normalization** (Logistic, Z-Score) within the additive Selection v2.1 architecture. While HPO identified a hybrid normalization protocol (Logistic for Momentum/Stability, Rank for others) as theoretically superior on raw metrics, a tournament battle confirmed that for the 2025 candidate pool, the additive model is highly robust, with the "magnitude-aware" champion yielding identical selections to the rank-sum baseline.

## 1. Methodology
- **Raw Metric Matrix**: Extracted unpruned mathematical values for 8 metrics (Returns, Vol, Liquidity, Entropy, etc.).
- **Normalization Archetypes**:
    - `rank`: Uniform mapping [0, 1].
    - `logistic`: S-curve mapping based on window Z-score.
    - `zscore`: Standard distance clipped at $\sigma$.
- **HPO Objective**: Maximize Risk-Adjusted Selection Alpha (Mean Alpha / Std Alpha).

## 2. HPO Findings
The Optuna study (500 trials) identified the following winning protocol:

| Metric | Normalization | Why? |
| :--- | :--- | :--- |
| **Momentum** | **Logistic** | Preserves alpha magnitude of extreme outperformers. |
| **Stability** | **Logistic** | Penalizes high-vol outliers more smoothly than ranks. |
| **Liquidity** | **Z-score** | Standardizes institutional volume depth. |
| **Survival** | **Rank** | Health is a relative gate; absolute values are noisy. |
| **Efficiency** | **Rank** | Predictability is best treated as a relative filter. |

**Best Risk-Adj Alpha (Unpruned Pool)**: 0.8751 (vs 0.7284 for pure Rank).

## 3. Tournament Results (Selection Alpha)
Comparison of architectures on 2025 data (Top N=5):

| Architecture | Mean Alpha | Vol (Std) | Risk-Adj Alpha |
| :--- | :--- | :--- | :--- |
| **v3.1 (Multiplicative)** | 0.58% | 3.41% | 0.17 |
| **v2.1 (Rank Baseline)** | 0.24% | 0.70% | **0.34** |
| **v2.1 (Optimized Multi-Norm)** | 0.24% | 0.70% | **0.34** |

### Observations:
1. **Robustness**: The v2.1 model is remarkably stable. Switching from Ranks to Logistic curves did not shift the top 5 selection set, confirming the structural integrity of the additive model.
2. **Stability vs Alpha**: v3.1 achieves higher raw alpha (0.58%) due to multiplicative aggression and vetoes, but suffers from 5x higher volatility (3.41%). v2.1 is the **Risk-Adjusted Champion**.

## 4. Final Recommendation
- **Standard**: Adopt the **Multi-Method Normalization** protocol in Production. While it yields identical results to ranks in the current regime, it provides **Magnitude Sensitivity** for future regimes where a single asset might exhibit extreme, statistically significant alpha magnitude that ranks would flatten.
- **Weights**: Update `weights_v2_1_global` to the new simplex-normalized values.
- **Top N**: Maintain `top_n=2` for maximum concentration, or `top_n=5` for diversified defensive runs.
