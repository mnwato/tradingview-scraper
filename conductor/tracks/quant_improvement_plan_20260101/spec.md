# Specification: Quantitative Improvement Plan 2026

## 1. Overview
This track performs a strategic post-mortem of the Grand Validation Tournament (2026-01-01) results. The goal is to evolve the "Selection Alpha" by solving the spectral degeneracy issue and standardizing optimizer reliability. It bridges the gap between raw implementation and production-ready robustness.

## 2. Functional Requirements

### 2.1 Spectral Integration Review (Architecture)
- **Deep Audit**: Analyze the returns of assets vetoed by the Entropy (>0.9) and Efficiency (<0.1) filters to determine if "high-noise" alpha was mistakenly discarded.
- **Architectural Exploration**: Compare three integration models:
    1. **Hard Veto** (Current): Discard asset if threshold is breached.
    2. **Score Penalty**: Multiply the MPS score by `(1 - Entropy)` or `Efficiency`.
    3. **Weight Regularizer**: Pass the predictability scores to the optimizer as a "noise penalty" cost term.

### 2.2 Engine Stability Audit (skfolio focus)
- **Edge Case Identification**: Isolate specific windows in 2025 where `skfolio` produced outlier results.
- **Factor Sensitivity**: Determine if the outliers are caused by covariance ill-conditioning (high kappa) or returns estimation variance.
- **Benchmark Update**: Produce a formal "Engine Reliability Matrix" for the documentation.

### 2.3 v3.1 Alpha Optimization
- **Attribution**: Identify the specific clusters/sectors where `v3.1` significantly outperformed `v2`.
- **Enrichment**: Explore adding 1-2 new features to the MPS scoring (e.g., skewness or kurtosis) to further improve the win rate.

## 3. Non-Functional Requirements
- **Evidence-Based Design**: All proposals in the Improvement Plan MUST be backed by data from the 2025 Grand Matrix.
- **Mathematical Rigor**: All new scoring/penalty formulas must be continuous and differentiable (if used in optimization).

## 4. Acceptance Criteria
- **Improvement Plan Document**: A finalized `docs/research/quantitative_improvement_plan_2026.md` containing:
    - Root cause analysis of spectral degeneracy.
    - Proposal for "Predictability Soft-Weighting".
    - Standardized "Optimizer Stability Guard" requirements.
- **Prototype Logic**: Refined `SelectionEngineV3_2` prototype code (or similar) implementing the proposed soft-weighting logic.

## 5. Out of Scope
- Implementing the entire improvement plan (this track is for Audit, Review, and Planning).
- Real-time trading tests.
