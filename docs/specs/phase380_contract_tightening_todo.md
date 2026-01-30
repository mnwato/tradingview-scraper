# TODO: Phase 380 — Contract Tightening (SDD + TDD)

This checklist implements Phase 380 requirements in `docs/specs/requirements_v3.md` (Section 8).

## Specs (What/Why)
- [x] Add Phase 380 requirements (candidate schema + strict gate + determinism) to `docs/specs/requirements_v3.md`.
- [x] Update DataOps spec to reflect candidate artifact naming and schema gate (`docs/specs/dataops_architecture_v1.md`).

## Design (How)
- [x] Design doc: `docs/design/contract_tightening_phase380_v1.md`

## TDD Targets
- [x] Test: consolidation normalizes heterogeneous candidate records to canonical schema.
- [x] Test: strict schema mode raises on invalid candidate records.

## Implementation Targets
- [x] Add candidate normalization helper: `tradingview_scraper/utils/candidates.py`
- [x] Enforce schema gate in DataOps consolidation: `scripts/services/consolidate_candidates.py`

## Verification
- [x] `uv run pytest -q tests/test_phase380_contract_tightening.py`
- [x] `make env-check`
