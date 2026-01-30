# Plan: Natural Selection Veto & ECI Scaling Audit

## Phase 1: Diagnostics
- [x] **Task**: Inspect `data/lakehouse/portfolio_candidates_raw.json` to see raw `Value.Traded` values for vetoed assets.
- [x] **Task**: Add debug logging to `natural_selection.py` to print individual ECI components (Vol, OrderSize, ADV) for a subset of assets.

## Phase 2: Code Fixes
- [x] **Task**: Refactor `enrich_candidates_metadata.py` to ensure `Value.Traded` is normalized to USD/Equivalent units.
- [x] **Task**: Update `NaturalSelectionEngine` in `engines.py` to use a `max_eci_impact` cap to prevent numerical blowups.
- [x] **Task**: Standardize the `ADV` fallback to the institutional floor (e.g., 100M for Futures) if scanner data is suspicious.

## Phase 3: Validation
- [x] **Task**: Rerun `make daily-run SELECTION_MODE=v3` and verify that at least some high-confidence Futures/Forex assets survive.
- [ ] **Task**: Update `AUDIT_REPORT.md` with findings on unit discrepancies.
