# Specification: Normalization Sensitivity Audit (v2.1)

## 1. Overview
This track investigates if the current ranking-based normalization in **Selection v2.1** discards critical information about the magnitude of alpha. By transitioning to a tunable normalization engine, we aim to preserve outlier information while maintaining the robustness of the additive model.

## 2. Functional Requirements

### 2.1 Normalization Engine
Implement a modular normalization system supporting:
- **`rank`**: Uniform percentile mapping [0, 1].
- **`zscore`**: Standardized distance from window mean, clipped at $\sigma$ units.
- **`logistic`**: S-curve mapping ($1 / (1 + e^{-z})$) for smooth dampening of outliers.
- **`minmax`**: Simple linear scaling relative to window extrema.

### 2.2 Raw Feature Caching
Update the feature caching pipeline to store **Raw Mathematical Values** (annualized returns, vol, liquidity in USD) instead of pre-processed probabilities.

### 2.3 Integrated HPO (Optuna)
- **Objective**: Maximize **Risk-Adjusted Selection Alpha**.
- **Search Space**:
    - `normalization_method`: Categorical (`rank`, `zscore`, `logistic`, `minmax`).
    - `clipping_sigma`: Float [1.0, 5.0] (for Z-score and Logistic).
    - `top_n`: Integer [2, 5].
    - Weights: 8-metric Simplex [0, 1].

## 3. Non-Functional Requirements
- **Bit-Identicality**: Replaying a run with the chosen method and weights must yield identical selections.
- **Interpretability**: Analyze the "Slope" of the normalization curve to ensure it doesn't over-emphasize noise.

## 4. Acceptance Criteria
- Identification of a normalization protocol that improves 2025 Sharpe ratio over the rank-only baseline.
- Formal tournament comparison between Multiplicative (v3.1) and optimized Additive (v2.1).
- Updated Research Report in `docs/research/normalization_audit_2026.md`.
