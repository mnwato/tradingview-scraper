# Plan: Predictability Feature Flags

## Phase 1: Settings Update
- [x] Task: Update `FeatureFlags` class in `tradingview_scraper/settings.py`. 8ee1ff7
- [x] Task: Add thresholds to `FeatureFlags` or main `Settings`. 8ee1ff7
- [x] Task: Update the CLI export mapping in `settings.py` to support these new flags. 8ee1ff7

## Phase 2: Selection Engine Update
- [x] Task: Refactor `SelectionEngineV3._select_v3_core` to check for feature flags. b9b1016
- [x] Task: Replace hardcoded thresholds with settings-based values. b9b1016
- [x] Task: Verify that `v3.1` (inheriting from `v3`) also respects these flags. b9b1016

## Phase 3: Verification [checkpoint: 814d6b9]
- [x] Task: TDD - Add test case to `tests/test_selection_predictability.py` to verify flag behavior. 814d6b9
- [x] Task: Run a "dry run" with flags disabled to ensure zero regressions in standard `v3`. 814d6b9
- [x] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md) 814d6b9
