# Specification: Artifact Paths & Summary Outputs
**Status**: Proposed
**Date**: 2025-12-28

## 1. Goals
- Keep the repo root clean by consolidating generated artifacts under `artifacts/`.
- Provide a stable “latest” view for operators and publishing.
- Preserve per-run archives for audit/debugging.
- Centralize path resolution via `pydantic-settings` so scripts don’t hardcode directories.

## 2. Canonical Summary Layout
All portfolio outputs that previously lived in `summaries/` move to:

```
artifacts/
  summaries/
    runs/
      <RUN_ID>/
        <output files>
    latest -> runs/<RUN_ID>
```

Notes:
- `runs/<RUN_ID>/` is the immutable per-run archive.
- `latest` is a symlink that points to the **last successful finalized** run directory.

## 3. Write Semantics
- All writers emit files into `artifacts/summaries/runs/<RUN_ID>/`.
- `latest` is promoted only after a successful finalize (see `make finalize` / `make promote-latest`).
- Publishing (`make gist`) syncs **only** `artifacts/summaries/latest/`, so it always reflects the last successful finalized run.

## 4. Configuration (pydantic-settings)
A settings object defines artifact directories.

Environment variables (prefix `TV_`):
- `TV_ARTIFACTS_DIR` (default: `artifacts`)
- `TV_SUMMARIES_DIR` (optional override; default: `<TV_ARTIFACTS_DIR>/summaries`)
- `TV_RUN_ID` (default: timestamp `YYYYMMDD-HHMMSS`; Makefile sets this to `RUN_ID`)
- `TV_LAKEHOUSE_DIR` (default: `data/lakehouse`)

The settings should expose:
- `summaries_run_dir = <summaries>/runs/<TV_RUN_ID>`
- `summaries_latest_link = <summaries>/latest`

## 4.1 Backtest / Tournament Outputs
Typical tournament artifacts (run-scoped):
- `artifacts/summaries/runs/<RUN_ID>/tournament_results.json`
- `artifacts/summaries/runs/<RUN_ID>/tournament_4d_results.json`
- `artifacts/summaries/runs/<RUN_ID>/full_4d_comparison_table.md`
- `artifacts/summaries/runs/<RUN_ID>/rebalance_audit_results.json`
- `artifacts/summaries/runs/<RUN_ID>/full_rebalance_comparison_table.md`
- `artifacts/summaries/runs/<RUN_ID>/returns/*.pkl`
- `artifacts/summaries/runs/<RUN_ID>/tearsheets/*.md`
- `artifacts/summaries/runs/<RUN_ID>/audit.jsonl`
- `artifacts/summaries/runs/<RUN_ID>/logs/*.log`

Notes:
- 4D outputs are optional and only appear when a selection-mode sweep or rebalance audit is executed.
- `logs/` is created by the production pipeline (`scripts/run_production_pipeline.py`). Ad-hoc scripts (e.g., `scripts/run_4d_tournament.py`) may not emit logs unless wrapped by the pipeline or explicitly instrumented.

## 5. Forex Analysis Outputs
Forex base-universe analysis (see `make forex-analyze`) writes run-scoped artifacts:
- `artifacts/summaries/runs/<RUN_ID>/forex_universe_report.md`
- `artifacts/summaries/runs/<RUN_ID>/forex_universe_report.csv`
- `artifacts/summaries/runs/<RUN_ID>/forex_universe_data_health.csv`
- `artifacts/summaries/runs/<RUN_ID>/forex_universe_clustermap.png`
- `artifacts/summaries/runs/<RUN_ID>/forex_universe_clusters.json`

## 6. Git Hygiene
- `artifacts/` is generated and must be ignored by git.
