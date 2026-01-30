# Specification: Optuna Hyperparameter Tuning (Log-MPS 3.2)

## 1. Overview
This track uses Optuna to optimize the asset selection parameters for the **Log-MPS 3.2** engine. We move beyond hard vetoes to a weighted log-probability model, tuning the impact of predictability metrics (Entropy, Hurst, Efficiency) to maximize **Pruning Expectancy (Selection Alpha)** across different market regimes. All new features are isolated with feature flags, and v3.2 must match or exceed v3.1 performance.

## 2. Functional Requirements

### 2.1 Refactor: Log-MPS 3.2 Standard
- Implement `SelectionEngineV3_2` using additive log-probabilities: $Score = \sum \omega_i \ln(P_i)$.
- Components: Momentum, Stability, Liquidity, Antifragility, Efficiency, Entropy, Hurst.
- **Probability Floor**: Use a floor (e.g., $10^{-9}$) to ensure finite log-scores.

### 2.2 Feature Flag Isolation
- Add `feat_selection_logmps` (default: `False`) to `FeatureFlags`.
- All `SelectionEngineV3_2` logic must be gated by this flag.
- Ensure that when the flag is `False`, the system defaults back to `SelectionEngineV3_1` logic.

### 2.3 Optuna Integration (Selection Tuning)
- **Objective Function**: Maximize `Selected EW Return - Raw EW Return` (Selection Alpha).
- **Study Mode**: Regime-Split Optimization.
    - **Study 1**: `NORMAL/QUIET` windows.
    - **Study 2**: `TURBULENT/CRISIS` windows.
- **Search Space**:
    - $\omega_{mom}, \omega_{stab}, \omega_{liq}, \omega_{af}, \omega_{er}, \omega_{pe}, \omega_{h} \in [0.0, 2.0]$.
    - Log-Relaxation of hard vetoes ($P_{min}$ thresholds).

### 2.4 Automated Study Pipeline
- Create `scripts/tune_selection_alpha.py` to automate the Optuna trials using the 2025 Grand Matrix data.
- **Feature Matrix Cache**: Pre-calculate all component probabilities to allow rapid Optuna iteration.

## 3. Non-Functional Requirements
- **Determinism**: Use fixed seeds for the Optuna `TPESampler`.
- **Performance Parity**: `v3.2` must be validated against `v3.1` to ensure no regression in alpha or stability.
- **Auditability**: The optimized weight sets must be logged in `audit.jsonl`.

## 4. Acceptance Criteria
- `SelectionEngineV3_2` successfully implemented and isolated by feature flag.
- Optuna identifying parameters that outperform `v3.1` in at least 70% of 2025 windows.
- Dynamic weight switching based on `MarketRegimeDetector` output is operational.
- Final report: `docs/research/hpo_selection_standard_2026.md`.

## 5. Out of Scope
- Tuning risk-engine parameters.
- Real-time execution tuning.
