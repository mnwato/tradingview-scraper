# Design: Phase 373 Modular Pipeline Safety (v1)

## 1. Purpose
Make modular pipelines (`tradingview_scraper/pipelines/*`) safe by default:
- prefer run-dir isolated artifacts,
- avoid silent reads from shared mutable lakehouse state,
- respect `TV_STRICT_ISOLATION=1`.

This is not a “new architecture” phase. It is a defaults + guardrails phase.

## 2. Scope
Primary targets:
- `tradingview_scraper/pipelines/selection/stages/ingestion.py`
- `tradingview_scraper/pipelines/selection/pipeline.py`

Out of scope:
- refactoring the entire selection pipeline execution to replace `scripts/*` entrypoints.

## 3. Design Rules

### 3.1 Run-Dir First
If a stage needs inputs (candidates/returns), it should resolve in this order:
1. Explicit constructor override path (caller provided)
2. Run-dir canonical paths derived from `SelectionContext.run_id`:
   - `settings.summaries_runs_dir / <run_id> / data / portfolio_candidates.json`
   - `settings.summaries_runs_dir / <run_id> / data / returns_matrix.parquet`
3. Legacy fallback to `settings.lakehouse_dir` only when `TV_STRICT_ISOLATION != 1`

### 3.2 Strict Isolation Gate
When `TV_STRICT_ISOLATION=1`:
- step (3) is forbidden
- missing run-dir inputs must raise `FileNotFoundError`

### 3.3 Logging
Whenever a fallback path is used, log a warning with:
- original requested run-id
- chosen fallback path

## 4. Acceptance Criteria (TDD)
1. With a run dir present, `IngestionStage.execute()` loads from run-dir even if lakehouse exists.
2. With `TV_STRICT_ISOLATION=1` and run-dir inputs missing, `IngestionStage.execute()` fails fast.
3. `SelectionPipeline` may be constructed without explicit candidate/returns paths; it delegates resolution to the stage safely.

