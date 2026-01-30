# Plan: Optuna Hyperparameter Tuning (Log-MPS 3.2)

## Phase 1: Core Refactor & Data Preparation [checkpoint: 789337a]
- [x] Task: Refactor `SelectionEngineV3` into the **Log-MPS 3.2** standard. 3d695a7
- [x] Task: Build the **Pre-Alpha Feature Matrix**. 789337a

## Phase 2: Regime-Split Optuna Studies [checkpoint: fb8fb54]
- [x] Task: Implement `scripts/tune_selection_alpha.py`. 789337a
- [x] Task: Execute **Regime-Split Studies**. fb8fb54

## Phase 3: Dynamic Integration & Performance Validation
- [x] Task: Implement **Dynamic Weight Switching**. fb8fb54
    - [ ] Sub-task: Update `SelectionEngineV3_2` to switch weights based on `MarketRegimeDetector` output.
    - [ ] Sub-task: Add optimized weights to `FeatureFlags` or a new configuration block.
- [~] Task: Validation Tournament & Final Report.
    - [ ] Sub-task: Run a comparison tournament: `v3.1` vs `v3.2` (Log-MPS).
    - [ ] Sub-task: Assert `v3.2` performance >= `v3.1` performance.
    - [ ] Sub-task: Write `docs/research/hpo_selection_standard_2026.md`.
- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)
