# Specification: Global Robust Selection Tuning (Log-MPS 3.2)

## 1. Overview
Transition from regime-specific weights to a single "Global Robust" weight set for the **Log-MPS 3.2** engine. This eliminates the dependency on the Market Regime Detector for asset selection and focuses on finding parameters that maximize **Selection Alpha** across the entire 2025 volatility spectrum.

## 2. Functional Requirements
- **Unified HPO**: Rerun Optuna using the entire `hpo_feature_cache.parquet` (all regimes combined).
- **Settings Update**: Add `weights_global` to `FeatureFlags` and `TradingViewScraperSettings`.
- **Logic Simplification**: Update `SelectionEngineV3_2` to use `weights_global` by default when `feat_selection_logmps` is enabled.

## 3. Non-Functional Requirements
- **Numerical Stability**: Maintain the $10^{-9}$ probability floor.
- **Explainability**: Log the relative contributions of each component in the final global set.

## 4. Acceptance Criteria
- Global weights identified that result in `v3.2` Sharpe >= `v3.1` Sharpe in a 2025 tournament.
- Reduced turnover compared to regime-split weights.
- Successful 100% bit-identical replay of validation using the global set.
