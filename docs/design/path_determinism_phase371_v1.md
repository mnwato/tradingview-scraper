# Design: Phase 371 Path Determinism Sweep (v1)

## 1. Purpose
Phase 371 removes hard-coded filesystem paths that make runs non-replayable across environments.

This phase is intentionally narrow:
- no portfolio logic changes,
- no optimizer changes,
- only path resolution and alignment semantics for tooling.

## 2. Design Rules

### 2.1 Use Settings as the Source of Truth
When a settings field exists, it MUST be used:
- `settings.summaries_runs_dir` for run lookup
- `settings.lakehouse_dir` for lakehouse artifacts
- `settings.export_dir` for discovery exports

### 2.2 Compatibility Pattern (Fallbacks)
Fallbacks may exist for legacy layouts, but MUST be:
1. settings-derived, and
2. explicit (log a warning that a fallback path was used).

## 3. Targeted Fixes

### 3.1 Meta/Validation: Correct run directory resolution
**Target**: `scripts/validate_meta_parity.py`

- Replace literal `Path("artifacts/summaries/runs/<RUN_ID>")` with:
  - `get_settings().summaries_runs_dir / run_id`
- Keep the “substring match” fallback but scoped to `settings.summaries_runs_dir`.

### 3.2 Meta scripts: Avoid `Path("data/lakehouse")`
**Targets**:
- `scripts/optimize_meta_portfolio.py`
- `scripts/flatten_meta_weights.py`

Replace `Path("data/lakehouse")` with `get_settings().lakehouse_dir`.

### 3.3 Modular pipeline defaults: avoid literal `data/lakehouse/...`
**Targets**:
- `tradingview_scraper/pipelines/selection/stages/ingestion.py`
- `tradingview_scraper/pipelines/selection/pipeline.py`

Prefer constructor defaults of `None`, and resolve defaults from settings inside `__init__`.

## 4. Alpha Read-Only & Network Isolation (CR-MLOps)

### 4.1 Unsafe Default Prevention
**Target**: `scripts/prepare_portfolio_data.py`

1. Change `PORTFOLIO_DATA_SOURCE` default from `"fetch"` to `"lakehouse_only"`.
2. Fail-fast if `"fetch"` is requested but `TV_STRICT_ISOLATION=1`.

### 4.2 Dead Import Cleanup
Remove reference to the non-existent `DataPipelineOrchestrator` in `prepare_portfolio_data.py`.

## 5. Acceptance Criteria (TDD)
1. `validate_meta_parity()` resolves the run directory via `settings.summaries_runs_dir`.
2. `validate_meta_parity()` does not pad missing returns with zeros (Phase 374 overlaps here).
3. Meta scripts use `settings.lakehouse_dir` for fallbacks.
4. Modular selection ingestion defaults are settings-driven.
5. `prepare_portfolio_data.py` defaults to read-only lakehouse mode.

