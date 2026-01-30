# Idea Honing (Q&A)

This file will capture the interactive requirements clarification process (one question at a time).

## Q1 (2026-01-21): Define “Faster Feedback Loop”

### Question
When you say “speed up the feedback loop” via **data + alpha pipeline cleanup/refactor**, which specific workflow(s) must become faster and tighter in practice?

Examples (pick the ones you care about, or name others):
- `make flow-dev` end-to-end iteration
- `make scan-run` discovery-only
- `make flow-data` ingestion/feature-only
- `make flow-production` but with reduced scope for iterative debugging
- `uv run pytest` / static checks turnaround

### Answer
Primary targets are:

- `make flow-data` (DataOps): identify the essential core steps and remove/skip/refactor steps that are ephemeral or non-functional for the main objective.
- Meta-portfolio flows (fractal / multi-sleeve): same cleanup goal—focus on essential core steps and rule out ephemeral / non-functional steps.

Goal: tighten iteration by clarifying what is truly required vs. optional overhead.

## Q2 (2026-01-21): Scope of “Core” vs “Ephemeral”

### Question
For these two targets (`flow-data` and meta-portfolio flows), should the “ephemeral / non-functional” steps be:

- removed/disabled only for **development/fast feedback** profiles, while keeping production unchanged, or
- removed/disabled for **all profiles including production** (i.e., the steps are genuinely unnecessary everywhere)?

### Answer
Disable by default in both production and development, unless explicitly opted-in.

## Q3 (2026-01-21): Opt-In Mechanism

### Question
What’s the preferred opt-in mechanism for these “ephemeral / non-functional” steps?

Pick one default (or specify another):
- A single Make flag, e.g. `EXTRAS=1 make flow-data` / `EXTRAS=1 make flow-meta`
- Per-namespace flags, e.g. `DATA_EXTRAS=1` and `META_EXTRAS=1`
- Feature flags via settings, e.g. `TV_FEATURES__FEAT_*` toggles in manifest/env

### Answer
Feature flags via settings (manifest/env-driven `TV_FEATURES__*` style toggles).

## Q4 (2026-01-21): Define Core Steps for `make flow-data`

### Question
For `make flow-data` (currently: `scan-run` → `data-ingest` → `meta-ingest` → `feature-ingest`), how do you want to classify each stage?

Please mark each as **CORE (always-on)** or **OPTIONAL (off by default; opt-in via feature flags)**:
- `scan-run`:
- `data-ingest`:
- `meta-ingest`:
- `feature-ingest`:

### Answer
All listed stages are **CORE**:
- `scan-run`: CORE
- `data-ingest`: CORE
- `meta-ingest`: CORE
- `feature-ingest`: CORE

## Q5 (2026-01-21): Define Core Steps for Meta-Portfolio Flow

### Question
For the meta-portfolio pipeline (`scripts/run_meta_pipeline.py`, stages: `meta.returns` → `meta.optimize` → `meta.flatten` → `meta.report`), how do you want to classify each stage?

Mark each as CORE (always-on) or OPTIONAL (off by default; opt-in via feature flags):
- `meta.returns` (aggregate sleeve returns):
- `meta.optimize` (allocate across sleeves):
- `meta.flatten` (collapse to physical assets):
- `meta.report` (markdown report generation):
- `execute_sleeves` (parallel sleeve production inside meta run):

### Answer
All listed stages are **CORE**:
- `meta.returns`: CORE
- `meta.optimize`: CORE
- `meta.flatten`: CORE
- `meta.report`: CORE
- `execute_sleeves`: CORE

## Q6 (2026-01-21): What Exactly Is “Ephemeral / Non-Functional”?

### Question
Given that all top-level stages for `flow-data` and the meta pipeline are CORE, which *specific* behaviors inside those stages do you want disabled-by-default (opt-in via feature flags) because they are “ephemeral” or “non-functional” for fast feedback?

To anchor: name concrete examples like “cache write/read”, “deep audit report generation”, “copy to `summaries/latest`”, “health gate strictness”, “enrichment retries”, “heavy validation passes”, etc.

### Answer
TBD
