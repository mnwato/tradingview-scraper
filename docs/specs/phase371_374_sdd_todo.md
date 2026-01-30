# TODO: Phases 371–374 (SDD + TDD)

This checklist operationalizes the remediation phases identified in `docs/specs/plan.md` Appendix D.

## Specs (What/Why)
- [x] Extend requirements with Phase 371–374 invariants (`docs/specs/requirements_v3.md`).
- [x] Reinforce path determinism in reproducibility spec (`docs/specs/reproducibility_standard.md`).

## Design (How)
- [x] Phase 371 design: `docs/design/path_determinism_phase371_v1.md`
- [x] Phase 372 design: `docs/design/alpha_readonly_enforcement_phase372_v1.md`
- [x] Phase 373 design: `docs/design/modular_pipeline_safety_phase373_v1.md`
- [x] Phase 374 design: `docs/design/validation_no_padding_phase374_v1.md`

## TDD Targets

### Phase 371: Path Determinism
- [x] Test: `validate_meta_parity` resolves run dir via `settings.summaries_runs_dir`.
- [x] Test: meta scripts use `settings.lakehouse_dir` for fallbacks (no `Path("data/lakehouse")`).
- [x] Test: modular selection ingestion defaults are settings-driven.

### Phase 373: Modular Pipeline Safety
- [x] Test: `IngestionStage` prefers run-dir inputs over lakehouse.
- [x] Test: `TV_STRICT_ISOLATION=1` denies lakehouse fallback.

### Phase 372: Alpha Read-Only Enforcement
- [x] Test: `prepare_portfolio_data` defaults to lakehouse-only mode.
- [x] Test: `prepare_portfolio_data` fails fast if non-lakehouse mode is requested.

### Phase 374: “No Padding”
- [x] Test: validation utilities do not `fillna(0.0)` to align returns (covered by parity test).
- [x] Test: alignment drops rows with NaNs and reports drop stats (covered by parity test).

## Implementation Targets
- [x] Fix `scripts/validate_meta_parity.py`:
  - use `settings.summaries_runs_dir`
  - remove `fillna(0.0)` padding, use dropna after asset restriction
  - log alignment loss stats
- [x] Fix `scripts/prepare_portfolio_data.py`:
  - default `PORTFOLIO_DATA_SOURCE` to `lakehouse_only`
  - fail fast on other values; remove or quarantine dead `DataPipelineOrchestrator` path
  - use settings-derived lakehouse paths for fallbacks
- [x] Fix meta scripts hard-coded lakehouse fallbacks:
  - `scripts/optimize_meta_portfolio.py`
  - `scripts/flatten_meta_weights.py`
- [x] Fix modular selection hard-coded defaults:
  - `tradingview_scraper/pipelines/selection/stages/ingestion.py`
  - `tradingview_scraper/pipelines/selection/pipeline.py`

- [x] Phase 373 safety hardening:
  - `tradingview_scraper/pipelines/selection/stages/ingestion.py` resolves run-dir first, lakehouse fallback only if not strict isolation
  - `tradingview_scraper/pipelines/selection/pipeline.py` passes `run_id` through context and relies on stage for safe resolution

## Verification
- [x] Run targeted tests for new phases: `uv run pytest -q tests/test_phase371_374_sdd.py`.
- [x] Run Phase 373 tests: `uv run pytest -q tests/test_phase373_modular_pipeline_safety.py`.
- [x] Run `make env-check`.
