# TODO: Phase 370 Correctness Hardening (SDD + TDD)

This is the concrete, test-first worklist for implementing the Phase 370 invariants defined in:
- `docs/specs/requirements_v3.md` (Section 6)
- `docs/design/correctness_hardening_phase370_v1.md`
- `docs/specs/plan.md` (Appendix C)

## 0) Preconditions
- [ ] Run `make env-check` and confirm manifest is valid.
- [ ] Confirm current branch is clean enough to run tests (`uv run pytest`).

## 1) Spec Updates (SDD)
- [x] Requirements: add Phase 370 invariants (`docs/specs/requirements_v3.md`).
- [x] Meta spec: forbid hard-coded manifest (`docs/specs/meta_streamlining_v1.md`).
- [x] DataOps spec: correct export path (`docs/specs/dataops_architecture_v1.md`).
- [x] Reproducibility spec: add “no hard-coded paths” (`docs/specs/reproducibility_standard.md`).

## 2) Design (SDD)
- [x] Create Phase 370 design doc: `docs/design/correctness_hardening_phase370_v1.md`.

## 3) Tests First (TDD)

### 3.1 Settings determinism
- [x] Add test: `get_settings().features.selection_mode` respects manifest defaults and env overrides.
- [x] Add test: stable default for `features.selection_mode` (implicit structural coverage).

### 3.2 Production orchestrator discovery validation
- [x] Add test: `ProductionPipeline.validate_discovery()` reads from `settings.export_dir / run_id`.

### 3.3 Ingestion lakehouse path consistency
- [x] Add test: `IngestionService(lakehouse_dir=...)` constructs a loader configured to the same path (no network).

### 3.4 Meta manifest resolution
- [x] Add test: `run_meta_pipeline(..., execute_sleeves=True)` loads the manifest from `settings.manifest_path` (or explicit `--manifest`).

### 3.5 Discovery scanner contract
- [x] Add test: `DiscoveryPipeline` calls scanners with params dict and normalizes `CandidateMetadata.identity` to `EXCHANGE:SYMBOL`.

## 4) Implementation (Make tests pass)
- [x] Remove duplicate `selection_mode` field in `tradingview_scraper/settings.py`.
- [x] Fix export path in `scripts/run_production_pipeline.py` validation.
- [x] Plumb `lakehouse_dir` into `PersistentDataLoader(lakehouse_path=...)` in `scripts/services/ingest_data.py`.
- [x] Add `--manifest` support and stop hard-coding manifest path in `scripts/run_meta_pipeline.py`.
- [x] Standardize discovery scanner params + identity normalization in `tradingview_scraper/pipelines/discovery/*`.

## 5) Verification Sweep
- [ ] Run unit tests: `uv run pytest -q` (blocked by unrelated collection errors in existing tests).
- [x] Run targeted unit tests: `uv run pytest -q tests/test_phase370_correctness_hardening.py`.
- [x] Run quick manifest validation: `make env-check`.
- [ ] Optional smoke (no network if possible): run meta/report generation on cached artifacts if available.

## 6) Forensic Follow-Ups
- [ ] If any change affects artifacts, update `docs/specs/audit_artifact_map.md`.
- [ ] If any behavior change affects production baselines, update `docs/specs/known_issues_v3.6.md`.
