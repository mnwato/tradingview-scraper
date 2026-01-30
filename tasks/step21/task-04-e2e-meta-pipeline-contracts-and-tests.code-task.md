---
status: pending
created: 2026-01-21
started: null
completed: null
---
# Task: E2E Meta Pipeline Contracts and Tests

## Description
Add end-to-end tests and minimal fixtures that validate a full meta-portfolio pipeline run produces the expected artifacts and respects key meta-portfolio invariants (calendar integrity, determinism, artifact contracts).

The goal is to ensure meta portfolios remain production-safe as the codebase evolves, especially across refactors that move logic from `scripts/` into `tradingview_scraper/`.

## Background
There are already unit and integration tests covering:
- `SleeveAggregator` and `WeightFlattener` behavior (`tests/test_meta_integration.py`)
- Ray orchestration dispatch and abort behavior (`tests/integration/test_ray_meta_orchestration.py`)

However, there is not yet a true E2E-style test that:
- creates a minimal “fake sleeve run artifact layout” on disk
- runs meta stages (returns → optimize → flatten → report)
- validates artifact paths, naming conventions, and core invariants

## Reference Documentation
**Required:**
- Design: docs/specs/multi_sleeve_meta_portfolio_v1.md

**Additional References (if relevant to this task):**
- docs/specs/fractal_meta_portfolio_v1.md (recursive behavior + physical asset collapse)
- docs/specs/meta_streamlining_v1.md (health guardrails + caching)

**Note:** You MUST read the detailed design document before beginning implementation. Read additional references as needed for context.

## Technical Requirements
1. Create a minimal “sleeve run artifact fixture” layout consistent with what meta stages read:
   - include `data/returns/*_{risk_profile}.pkl` (or the canonical locations your implementation uses)
   - include minimal `audit.jsonl` / `resolved_manifest.json` entries if required for run lookup/health
2. Ensure tests do not perform network calls and are deterministic.
3. Validate the full meta pipeline produces:
   - `meta_returns_{meta_profile}_{risk_profile}.pkl`
   - `meta_manifest_{meta_profile}_{risk_profile}.json`
   - `meta_optimized_{meta_profile}_{risk_profile}.json`
   - `portfolio_optimized_meta_{meta_profile}_{risk_profile}.json`
   - a markdown report (e.g., `reports/meta_portfolio_report.md`)
4. Validate core invariants:
   - inner join calendar semantics (no weekend padding)
   - stable sleeve weight bounds if configured (min/max)
   - recursive behavior works for nested `meta_profile` sleeves (at least one test tree of depth 2)
5. Include unit test coverage requirements for any new helper functions/classes introduced to support the E2E runner.

## Dependencies
- Meta stage implementations and registration (Tasks 01–03)
- `pytest` fixtures and temp directory utilities
- `configs/manifest.json` meta profile structure (or generate a minimal manifest for tests)

## Implementation Approach
1. Add a new integration test module (e.g., `tests/integration/test_meta_pipeline_e2e.py`).
2. Use `tmp_path` to create:
   - fake `data/artifacts/summaries/runs/<RUN_ID>/...` run directories for atomic sleeves
   - a meta run directory to write outputs into
3. Patch `get_settings()` paths so that meta stages look at the temp artifacts directory for sleeve runs.
4. Run the canonical meta pipeline runner and assert on output artifact existence + content sanity:
   - return matrix columns match sleeve IDs
   - weights sum approximately to 1.0
   - flattened weights contain expected physical symbols
5. Keep fixtures minimal to avoid brittle tests.

## Acceptance Criteria

1. **Artifact Contract**
   - Given a temporary workspace with two sleeve runs
   - When executing the meta pipeline stages end-to-end
   - Then all expected meta artifacts exist in the meta run directory with correct naming conventions.

2. **Calendar Integrity**
   - Given sleeve return series containing different calendars (including weekends)
   - When building meta returns
   - Then the meta return matrix index is the intersection of dates (inner join), with no inserted weekend rows.

3. **Weight Bounds**
   - Given a meta profile with `min_weight` and `max_weight` configuration
   - When running meta optimization
   - Then output sleeve weights respect those bounds (or the test asserts an explicit, documented exception behavior).

4. **Nested Meta Support**
   - Given a meta profile that includes a nested `meta_profile` sleeve
   - When building returns and flattening
   - Then recursion resolves and the final flattened portfolio contains only physical assets with summed weights.

5. **Unit/Integration Test Coverage**
   - Given the added E2E behavior
   - When running `pytest`
   - Then the new E2E tests pass and cover the primary failure modes (missing artifacts, health veto, join policy).

## Metadata
- **Complexity**: High
- **Labels**: Meta, E2E, Testing, Contracts, Reproducibility
- **Required Skills**: pytest fixtures, filesystem-based testing, deterministic pipelines, Pandas

