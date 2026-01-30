---
status: pending
created: 2026-01-21
started: null
completed: null
---
# Task: Implement Meta Stages Under Package-Owned Pipelines

## Description
Implement the canonical meta stages (`meta.returns`, `meta.optimize`, `meta.flatten`, `meta.report`) inside the `tradingview_scraper` package, reusing the existing meta pipeline modules and aligning with workspace isolation standards.

This task removes the primary source of drift between scripts and library code by making the package implementation the “single source of truth” for meta stage logic, while leaving scripts as thin wrappers.

## Background
The repo already contains `tradingview_scraper/pipelines/meta/` with:
- `MetaContext` (`base.py`)
- `SleeveAggregator` (`aggregator.py`)
- `WeightFlattener` (`flattener.py`)

However, the meta stages currently executed in production are implemented in `scripts/*`, and those implementations also handle recursion, caching, artifact naming, and reporting. This split introduces risk:
- behavior differences between module and script implementations
- stage registry depending on script imports
- inconsistent output paths and run isolation

## Reference Documentation
**Required:**
- Design: docs/specs/multi_sleeve_meta_portfolio_v1.md

**Additional References (if relevant to this task):**
- docs/specs/fractal_meta_portfolio_v1.md (recursive nesting + flattening requirements)
- docs/specs/meta_streamlining_v1.md (caching + health guardrails)
- docs/design/orchestration_layer_v1.md (stage contract expectations)

**Note:** You MUST read the detailed design document before beginning implementation. Read additional references as needed for context.

## Technical Requirements
1. Provide package-owned implementations for:
   - `meta.returns`: build sleeve returns matrix (including recursive meta nesting)
   - `meta.optimize`: solve for sleeve weights by risk profile (hrp/min_var/etc.)
   - `meta.flatten`: project sleeve weights down to physical assets (recursive collapse)
   - `meta.report`: generate forensic markdown report
2. Enforce workspace isolation:
   - all outputs must be written under the active run directory (e.g., `data/artifacts/summaries/runs/<RUN_ID>/data/` and `.../reports/`)
   - avoid polluting `data/lakehouse` unless explicitly configured for caching
3. Preserve parity constraints:
   - meta profiles use philosophy-matched sleeve return streams (Meta-HRP uses sleeve HRP streams, etc.)
   - enforce inner-join semantics for cross-calendar sleeves (no weekend padding)
4. Maintain health guardrails (e.g., 75% optimization health threshold) for sleeve inclusion.
5. Keep artifact naming consistent and prefixed by `meta_profile` to avoid collisions.
6. Ensure stages are registered via `StageRegistry` with stable IDs and categories/tags.

## Dependencies
- `configs/manifest.json` meta profiles (e.g., `meta_production`, `meta_benchmark`, etc.)
- `tradingview_scraper/settings.py` run directory conventions
- `tradingview_scraper/portfolio_engines/*` and meta optimization request types
- Existing implementations in `scripts/build_meta_returns.py`, `scripts/optimize_meta_portfolio.py`, `scripts/flatten_meta_weights.py`, `scripts/generate_meta_report.py` for parity/reference

## Implementation Approach
1. Create package stage modules under `tradingview_scraper/pipelines/meta/` (e.g., `stages.py`) implementing each stage as a function with explicit parameters.
2. Port logic from the existing scripts carefully:
   - caching: keep cache in `data/lakehouse/.cache` but write “run outputs” into the run directory
   - recursion: ensure nested `meta_profile` sleeves are handled deterministically
   - manifest outputs: persist `meta_manifest_{meta_profile}_{risk_profile}.json` to run dir
3. Ensure `meta.optimize` can infer the base directory from `returns_path` (consistent with the isolation standard).
4. Keep the scripts as wrappers:
   - scripts should call the package stage functions (or `QuantSDK.run_stage`) rather than re-implementing logic.
5. Add/update tests for stage-level behavior using small in-memory or temp-dir artifacts:
   - meta aggregation join behavior (inner join + timezone normalization)
   - flattening sums identical assets across sleeves and preserves direction handling
   - report generation produces expected sections and doesn’t crash on missing optional artifacts

## Acceptance Criteria

1. **Package-Owned Stage Implementations**
   - Given the repository codebase
   - When inspecting the registered stage callables for `meta.*`
   - Then the implementations live under `tradingview_scraper/pipelines/meta/` (not only in `scripts/*`).

2. **Workspace Isolation**
   - Given a `RUN_ID` and a run data directory
   - When running the meta stages in sequence
   - Then all produced artifacts are written inside the run directory, and do not require writing into `data/lakehouse` except optional caching.

3. **Calendar Integrity**
   - Given sleeve return series with mismatched dates (including weekends)
   - When building meta returns
   - Then the meta returns matrix uses inner join semantics and never zero-fills missing dates.

4. **Health Guardrails**
   - Given a sleeve that fails the health threshold
   - When building meta returns
   - Then that sleeve is excluded and the decision is recorded in logs/audit artifacts.

5. **Unit Test Coverage**
   - Given the stage implementations
   - When running the test suite
   - Then the key behaviors above are validated by unit/integration tests.

## Metadata
- **Complexity**: High
- **Labels**: Meta, Pipelines, Fractal, Workspace Isolation, Risk, Reporting
- **Required Skills**: Pandas, file/dir isolation patterns, refactoring scripts into library code, unit testing

