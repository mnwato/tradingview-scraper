# Plan: Quantitative Improvement Plan 2026

## Phase 1: Deep Audit & Spectral Analysis
- [x] Task: Audit Spectral Vetoes in the 2025 Grand Matrix.
    - [x] Sub-task: Extract list of symbols vetoed by Entropy/Efficiency in every window.
    - [x] Sub-task: Calculate "Opportunity Cost" (Total return of vetoed assets vs selected assets).
    - [x] Sub-task: Identify if specific asset classes (e.g. Crypto) are unfairly penalized.
- [x] Task: Research Integration Models for Predictability.
    - [x] Sub-task: Propose mathematical formula for "Soft-Weighting" (e.g. MPS * Efficiency).
    - [x] Sub-task: Research "Predictability-Adjusted Returns" for the optimizer.
- [x] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Engine Stability & skfolio Audit
- [x] Task: Isolate skfolio Outlier Windows.
    - [x] Sub-task: Identify specific windows where skfolio deviation from group mean was >2σ.
    - [x] Sub-task: Correlation check between outlier magnitude and covariance Condition Number (kappa).
- [x] Task: Perform Factor Sensitivity Analysis.
    - [x] Sub-task: Check if skfolio sensitivity is driven by the Returns Estimator vs Covariance.
    - [x] Sub-task: Draft the "Engine Reliability Matrix" for docs.
- [x] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: Strategy Evolution & Final Improvement Plan
- [x] Task: Analyze v3.1 Alpha Success.
    - [x] Sub-task: Perform Sector/Cluster attribution for v3.1 top-performing windows.
    - [x] Sub-task: Evaluate adding Higher-Order Moment features (Skewness, Kurtosis) to MPS.
- [x] Task: Finalize Improvement Plan & Prototype.
    - [x] Sub-task: Write `docs/research/quantitative_improvement_plan_2026.md`.
    - [x] Sub-task: TDD - Implement `SelectionEngineV3_2` prototype with soft-weighting logic.
    - [x] Sub-task: Verify prototype logic with unit tests.
- [x] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)
