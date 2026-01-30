# Plan: Pipeline Efficiency & Scoring Consolidation

## Phase 1: select_top_universe.py Refactor
- [x] **Task**: Remove `_alpha_score` logic.
- [x] **Task**: Update Venue selection to use `Value.Traded` as the primary tie-breaker for Identities.
- [x] **Task**: Relax `UNIVERSE_TOTAL_LIMIT` to 200 and remove asset-class-specific hard caps.

## Phase 2: prepare_portfolio_data.py Cleanup
- [x] **Task**: Remove `_resolve_export_dir()` and legacy `export/*.json` loop.
- [x] **Task**: Standardize the candidate loading to strictly use `CANDIDATES_FILE`.

## Phase 3: natural_selection.py Audit
- [x] **Task**: Verify `id_to_best` logic correctly picks the Log-MPS winner within clusters.
- [x] **Task**: Ensure `antifragility_stats.json` is correctly merged with the consolidated metadata.

## Phase 4: Verification
- [x] **Task**: Rerun `make run-daily` up to `Step 5` and verify `selection_audit.json` shows correctly consolidated venues.
- [x] **Task**: Fix `Makefile` bug where `SELECTION_MODE` defaulted to `1`.
