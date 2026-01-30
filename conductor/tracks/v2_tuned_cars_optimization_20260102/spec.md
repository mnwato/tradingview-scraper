# Specification: Selection v2.1 (Tuned CARS Optimization)

## 1. Overview
This specification formalizes **Selection v2.1**, an optimized evolution of the Additive Rank-Sum model (CARS 2.0). By applying Optuna HPO to a 100% walk-forward matrix of 2025, we identify the optimal additive weights for momentum, stability, and predictability metrics. This serves as the primary architectural competitor to the Multiplicative/Log-MPS (v3.x) series.

## 2. Functional Requirements

### 2.1 Refactor: SelectionEngineV2_1
- Implementation of `SelectionEngineV2_1` using additive weighted ranks: $Score = \sum \omega_i \text{Rank}(X_i)$.
- Components (8-Metric Standard):
    - Core: Momentum, Stability, Liquidity, Antifragility, Survival.
    - Spectral: Efficiency, Entropy, Hurst.
- Normalization: Input metrics must be ranked/percentiled before applying weights to ensure scale-invariance.

### 2.2 Additive HPO (Optuna)
- **Objective Function**: Maximize **Risk-Adjusted Selection Alpha** ($Mean(Alpha) / Std(Alpha)$).
- **Study Mode**: Global Robust Tuning across all 2025 windows.
- **Search Space**:
    - $\omega_i \in [0.0, 1.0]$ for all 8 components.
    - `top_n` breadth $\in [2, 5]$.
    - Constraint: Weights should be normalized to sum to 1.0 (Simplex Search).

### 2.3 Feature Flag isolation
- Add `feat_selection_v2_1` (default: `False`) to `FeatureFlags`.
- All `v2.1` logic must be gated by this flag or the `v2.1` mode selection.

## 3. Non-Functional Requirements
- **Stability**: Additive models are expected to exhibit lower window-to-window rotation (turnover) than Log-MPS models.
- **Explainability**: Weights must be directly interpretable as "percentage contribution" to the final score.

## 4. Acceptance Criteria
- `SelectionEngineV2_1` successfully identifies a global weight set that outperforms the hardcoded `v2` baseline.
- Formal "Battle of Architectures" tournament comparing `v3.1`, `v3.2`, and `v2.1`.
- Research report: `docs/research/battle_of_architectures_2026.md`.
