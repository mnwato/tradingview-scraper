# Design: Phase 370 Correctness Hardening (v1)

## 1. Purpose
This design document translates the Phase 370 requirements (see `docs/specs/requirements_v3.md`) into concrete code changes and TDD targets.

Phase 370 is about preventing **silent drift**:
- wrong default values due to duplicated config fields,
- incorrect filesystem paths due to hard-coded strings,
- non-replayable behavior due to hard-coded manifest loads,
- inconsistent identity formats across discovery → ingestion → portfolio.

## 2. Scope

### In Scope
1. Settings determinism for `features.selection_mode`.
2. Export path correctness for discovery validation in the production orchestrator.
3. Lakehouse path consistency for data ingestion + toxicity validation.
4. Meta pipeline manifest resolution for sleeve execution.
5. Discovery scanner interface consistency and candidate identity normalization.

### Out of Scope
- Any research changes to selection ranking logic (e.g., short-side score ordering), unless needed for invariants above.
- Live trading / OMS / MT5.

## 3. Design Changes

### 3.1 Settings: Single `selection_mode`
**Problem**
- `FeatureFlags` currently declares `selection_mode` more than once, creating implicit override behavior.

**Change**
- Ensure `FeatureFlags.selection_mode` exists exactly once.
- Keep the default aligned with the institutional manifest default (currently `v4`), unless an explicit profile override exists.

**Acceptance Criteria**
- With no manifest-provided selection mode, `get_settings().features.selection_mode` equals the documented default.
- With manifest defaults set, manifest wins.
- With env override `TV_FEATURES__SELECTION_MODE`, env wins.

### 3.2 Production Orchestrator: Discovery export path
**Problem**
- `ProductionPipeline.validate_discovery()` checks `export/<RUN_ID>` but DataOps writes to `data/export/<RUN_ID>` (`settings.export_dir`).

**Change**
- Replace hard-coded `Path("export")` with `get_settings().export_dir`.

**Acceptance Criteria**
- If `settings.export_dir / RUN_ID` contains json files, validate_discovery reports the correct count.

### 3.3 Ingestion: Lakehouse path consistency
**Problem**
- `IngestionService` can accept `--lakehouse`, but it constructs `PersistentDataLoader()` without plumbing that path through.
- The validator then checks `self.lakehouse_dir`, which can differ from where the loader wrote.

**Change**
- Construct `PersistentDataLoader(lakehouse_path=str(self.lakehouse_dir))` so the writer and validator share the same base path.

**Acceptance Criteria**
- In tests, a custom lakehouse dir results in a loader configured to that same dir.

### 3.4 Meta Orchestrator: Manifest resolution
**Problem**
- `scripts/run_meta_pipeline.py` hard-codes `configs/manifest.json` in the sleeve execution path.

**Change**
- Add `--manifest` CLI arg and plumb it into `TV_MANIFEST_PATH`.
- Always load via `settings.manifest_path` once settings are initialized.

**Acceptance Criteria**
- Meta pipeline uses the specified manifest when running `--execute-sleeves`.

### 3.5 Discovery: Params + identity normalization
**Problem**
- `BaseDiscoveryScanner.discover(params: Dict)` conflicts with current usage (`discover(str(path))`).
- Candidate identity can become double-prefixed (`EXCHANGE:EXCHANGE:SYMBOL`) if `symbol` is already an identity.

**Change**
- Standardize discovery invocation as `discover({"config_path": "...", "interval": "...", ...})`.
- Normalize TradingView discovery rows:
  - if `row["symbol"]` contains `EXCHANGE:SYMBOL`, parse it into `exchange` and bare `symbol`.
  - set `CandidateMetadata.identity` to exactly `EXCHANGE:SYMBOL`.

**Acceptance Criteria**
- Unit tests verify scanner interface is stable and identity is single-prefixed.

## 4. TDD Plan (Test Targets)
Tests should be minimal, deterministic, and not require network calls.

1. `test_settings_selection_mode_default_and_override`
2. `test_production_validate_discovery_uses_settings_export_dir`
3. `test_ingestion_service_plumbs_lakehouse_path_to_persistent_loader`
4. `test_meta_pipeline_uses_settings_manifest_path_for_execute_sleeves`
5. `test_tradingview_discovery_normalizes_identity`

## 5. Rollout / Safety
- These changes are correctness-only and should not change portfolio results when manifests explicitly define the relevant settings.
- Any behavior change MUST be reflected in `docs/specs/known_issues_v3.6.md` if it impacts existing baselines.

