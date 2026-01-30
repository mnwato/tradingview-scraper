# Plan: Global Robust Selection Tuning (Log-MPS 3.2)

## Phase 1: Global Tuning & Settings Update
- [ ] Task: Modify `scripts/tune_selection_alpha.py` to support a `global` study mode.
- [ ] Task: Execute 500-trial Optuna study on all 2025 windows.
- [ ] Task: Update `tradingview_scraper/settings.py` with the new `weights_global`.
- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Engine Integration & Final Validation
- [ ] Task: Refactor `SelectionEngineV3_2.select` to use global weights by default.
- [ ] Task: Rerun `scripts/validate_hpo_selection.py` comparing `v3.1` vs `v3.2_global`.
- [ ] Task: Update `docs/research/hpo_selection_standard_2026.md` with Global Robustness findings.
- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)
