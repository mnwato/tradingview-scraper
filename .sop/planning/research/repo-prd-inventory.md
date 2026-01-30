# Repo PRD / Design Inventory (Local-Only)

This note inventories the **existing** PRD-like documents and design/spec artifacts already present in this repository, to avoid duplicating work and to treat the repo as the source-of-truth baseline.

## Primary “Product / PRD” Sources

These read most like a PRD or product charter (goals, target users, outcomes).

- `README.md`
  - Product positioning (“institutional-grade”), capability list, primary entrypoints (`make daily-run`, `make tournament`, etc.).
- `conductor/product.md`
  - Explicit product goals and feature set (audit ledger, spectral predictability, selection alpha vs optimization alpha, etc.).
- `AGENTS.md`
  - Institutional operating principles for the quant platform (3-pillar architecture, selection standards, feature flags, audit integrity, and “no padding” calendar rules).

## Primary “System / Architecture / Specs” Sources

These documents define architecture, configuration contracts, and operational workflow.

- `Makefile`
  - The effective pipeline topology (targets like `scan-run`, `flow-data`, `data-prep-raw`, `port-select`, `port-optimize`, `port-test`).
  - The manifest → env-bridge via `python -m tradingview_scraper.settings --export-env`.
- `configs/manifest.json` + `configs/manifest.schema.json`
  - Schema-validated workflow profiles and defaults.
  - Profile aliasing (e.g., `production` → `production_2026_q1`).
  - Meta-fractal profiles (multi-sleeve meta-portfolios).
- `docs/specs/workflow_manifests.md`
  - Manifest precedence/resolution order and reproducibility standards.
- `docs/design/selection_pipeline_v4_mlops.md`
  - “MLOps-centric” pipeline decomposition: ingestion → features → inference → partitioning → policy → synthesis.
  - Audit ledger / observability expectations for selection stages.
- `docs/design/layered_pipelines.md`
  - Scanner/pipeline composition hierarchy L0–L4 (universe → hygiene → templates → strategy blocks → pipeline entry).
- `docs/operations/runbook.md`
  - Operational scheduling (data cycle, alpha cycle, crypto cycle) and common failure handling.

## “Fractal / Meta-Portfolio” Sources (Directly Relevant)

These are directly aligned with the rough idea (“fractal portfolios optimization”).

- `docs/design/fractal_framework_v1.md` (Created: 2026-01-21)
  - Consolidation plan into a modular “Fractal Framework” that explicitly says to **extend existing patterns** rather than add parallel abstractions.
  - Calls out gaps to formalize: discovery module, filters extraction, meta-portfolio formalization.
- `docs/specs/fractal_meta_portfolio_v1.md`
  - Spec for meta-portfolio orchestration across sleeves (treat sleeve outputs as “assets”).
- `docs/reports/fractal_meta_audit_20260118.md`
  - Audit evidence/observations about the fractal/meta approach (useful for acceptance criteria).
- `configs/manifest.json` meta profiles:
  - `meta_production`, `meta_crypto_only`, `meta_fractal_test`, `meta_benchmark`.

## “Planning / Track” Docs (Large Backlog)

There is an extensive set of planning/spec/report artifacts under:

- `conductor/tracks/**` (many `plan.md`, `spec.md`, `report.md`)
- `docs/plan/**`
- `docs/audit/**`
- `.opencode/plans/**`

These likely contain the most detailed operational/acceptance criteria and audit outcomes, but they are too numerous to treat as a single PRD.

### Suggested way to use them
- Treat `README.md` + `conductor/product.md` + `docs/specs/workflow_manifests.md` as the “PRD spine”.
- Use a *small* subset of `docs/design/**` + the relevant `docs/plan/**` / `docs/audit/**` files as “design + acceptance evidence”.
- Pull track docs only when a design decision needs justification or a prior audit already resolved a question.

## Initial Gaps / Unknowns for Our New Work

Even with all the above in place, the repo does not fully pin down (yet) what “fractal portfolios optimization” means for the next increment:

- Whether “fractal” means **multi-sleeve only**, or also **multi-horizon within a sleeve** (e.g., 5/20/60d) as first-class sleeves.
- Whether the “MLOps pipelines” are intended to be:
  - v4 **selection** pipeline only, or
  - a wider “data → selection → optimization → reporting” pipeline framework with uniform stage interfaces.
- What the concrete user-facing deliverable is (CLI, config additions, scheduler changes, new artifacts, new reports).

