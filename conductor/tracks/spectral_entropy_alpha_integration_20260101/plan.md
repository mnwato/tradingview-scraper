## Phase 1: Shared Core & Refactor [checkpoint: 968da0a]
- [x] Task: Implement `tradingview_scraper/utils/predictability.py` with ER, PE, and Hurst functions. 968da0a
- [x] Task: Refactor `tradingview_scraper/regime.py` to use the shared predictability utility. 968da0a
- [x] Task: Unit tests for shared utility using synthetic data (Random Walk, Trending, Noisy). 968da0a

## Phase 2: Selection Engine Implementation (V3) [checkpoint: b59a155]
- [x] Task: Update `SelectionEngineV3` to calculate asset-level predictability metrics. b59a155
- [x] Task: Implement the "Predictability Vetoes" logic (Entropy, Efficiency, Hurst Random Walk). b59a155
- [x] Task: Integrate Efficiency Ratio as a scoring multiplier in MPS. b59a155
- [x] Task: Verify that vetoes are correctly logged in the `SelectionResponse`. b59a155

## Phase 3: Validation & Auditing [checkpoint: 3a4122d]
- [x] Task: Run a tournament comparing `v3` vs `v3.1_spectral` (using new filters). 3a4122d
- [x] Task: Verify `audit.jsonl` contains the expected "Vetoed: Predictability" entries. 3a4122d
- [x] Task: Final Report: `docs/research/spectral_alpha_results_2026.md`. 3a4122d
- [x] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md) 3a4122d
