# Configuration & Reproducibility (Manifest-Driven)

This document summarizes how configuration is expressed and resolved in this repo, and what reproducibility/audit contracts already exist.

## Canonical Configuration Surface

- `configs/manifest.json`: single source-of-truth for defaults + profiles
- `configs/manifest.schema.json`: schema validation + IDE autocomplete
- `Makefile`: bridges manifest/profile values into environment variables for script compatibility
- `tradingview_scraper.settings` module: exports resolved environment (`--export-env`) and provides settings injection

## Profile Aliasing (Example: `production`)

Per `docs/specs/workflow_manifests.md`, the manifest supports profile aliasing.

- `configs/manifest.json` uses:
  - `profiles.production` as an alias (string) → currently points to `production_2026_q1`
  - `profiles.production_2026_q1` as an immutable snapshot

This matches the “institutional reproducibility” standard: production is a stable pointer, snapshots are historical truth.

## Mermaid: Settings Resolution / Precedence

The repo documents a 6-layer precedence order.

```mermaid
flowchart TB
  A[CLI flags / init args] --> F[Effective Settings]
  B[.env (dotenv)] --> F
  C[OS env vars (TV_*)] --> F
  D[Active manifest profile] --> F
  E[Manifest defaults] --> F
  G[Code defaults] --> F
```

## Makefile Bridge

The Makefile resolves and exports settings by running:

- `python -m tradingview_scraper.settings --export-env`

It also supports shorthand overrides (examples):

- `LOOKBACK=<n>` → promoted to `TV_LOOKBACK_DAYS`
- `BACKTEST_TRAIN=<n>` → promoted to `TV_TRAIN_WINDOW`
- `BACKTEST_TEST=<n>` → promoted to `TV_TEST_WINDOW`
- `BACKTEST_STEP=<n>` → promoted to `TV_STEP_SIZE`
- `SELECTION_MODE=<mode>` → promoted to `TV_FEATURES__SELECTION_MODE`

This means “pipelines should be toggled by env/CLI” is already a first-class workflow.

## Reproducibility Artifacts

Per `docs/specs/workflow_manifests.md` and repo conventions:

- Every run has a `RUN_ID` (`TV_RUN_ID`) used as the primary namespace for artifacts.
- Run outputs land under: `data/artifacts/summaries/runs/<RUN_ID>/`
- A manifest snapshot is expected to be archived in run-scoped directories (the exact filename may vary by orchestration path, but the expectation is explicit).

## Audit / Ledger Expectations

Across `AGENTS.md`, `docs/specs/workflow_manifests.md`, and `conductor/product.md`:

- Auditability is non-negotiable for production decisions.
- Selection decisions should be recorded to an append-only ledger (commonly referenced as `audit.jsonl`).
- Some docs describe chained hashes (SHA-256) for ledger integrity.

## Why This Matters for “MLOps Pipelines”

If the rough idea is to add “MLOps-style pipelines to scan, filter, rank”, the repo already contains:

- A manifest-driven config layer (profiles, defaults, flags)
- A stage-based selection pipeline spec (v4)
- A run-scoped artifact and audit philosophy

So the likely work is **formalization and integration**, not inventing new configuration or tracking mechanisms.

## Open Questions to Clarify Later

- Which pipelines are “in scope” for MLOps formalization:
  - selection-only stages, or end-to-end (scan→data→selection→optimize→meta)?
- How strict should reproducibility be for experimental runs:
  - always archive manifests + ledger, or allow “fast/dev” modes that skip heavy artifacts?

