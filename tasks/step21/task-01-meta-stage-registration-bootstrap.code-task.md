---
status: pending
created: 2026-01-21
started: null
completed: null
---
# Task: Meta Stage Registration Bootstrap

## Description
Make meta-portfolio stages (`meta.returns`, `meta.optimize`, `meta.flatten`, `meta.report`) discoverable and runnable deterministically via `StageRegistry` and `QuantSDK`, without relying on accidental side-effect imports from `scripts/`.

This enables reliable end-to-end (E2E) meta-portfolio pipelines, makes `scripts/quant_cli.py stage list/run` useful in fresh processes, and removes a fragile dependency where stage registration only happens if specific `scripts/*.py` files are imported first.

## Background
The repo currently registers meta stages using decorators in `scripts/build_meta_returns.py`, `scripts/optimize_meta_portfolio.py`, `scripts/flatten_meta_weights.py`, and `scripts/generate_meta_report.py`. This creates an implicit side-effect dependency: unless those script modules are imported, the stage registry is empty.

The meta pipeline entrypoint `scripts/run_meta_pipeline.py` calls `QuantSDK.run_stage("meta.*")`, but `QuantSDK` currently does not ensure stage modules are imported/registered. This prevents reproducible stage discovery and makes meta orchestration brittle.

## Reference Documentation
**Required:**
- Design: docs/specs/multi_sleeve_meta_portfolio_v1.md

**Additional References (if relevant to this task):**
- docs/design/orchestration_layer_v1.md (StageRegistry/SDK intent)
- docs/specs/fractal_meta_portfolio_v1.md (stage list expectations)

**Note:** You MUST read the detailed design document before beginning implementation. Read additional references as needed for context.

## Technical Requirements
1. Ensure meta stages are registered from within `tradingview_scraper` (package-owned), not only from `scripts/`.
2. Provide a deterministic import/registration pathway so `StageRegistry.list_stages()` returns meta stages in a new process.
3. Maintain backwards compatibility: existing `scripts/*` entrypoints should continue to work.
4. Keep stage IDs stable (`meta.returns`, `meta.optimize`, `meta.flatten`, `meta.report`) to preserve orchestration references.
5. Add unit/integration tests asserting stage discovery works without importing `scripts/*` explicitly.

## Dependencies
- `tradingview_scraper/orchestration/registry.py` (StageRegistry)
- `tradingview_scraper/orchestration/sdk.py` (QuantSDK)
- Existing meta pipeline logic currently in `scripts/*` (to be migrated in later tasks)

## Implementation Approach
1. Introduce a package-level registration module (e.g., `tradingview_scraper/orchestration/stages.py` or `tradingview_scraper/pipelines/meta/stages.py`) that imports/declares meta stage callables.
2. Update `QuantSDK.run_stage()` (or CLI startup) to ensure the registration module is imported once per process before lookup.
3. Keep `scripts/*.py` stage decorators either removed later (after migration) or treated as legacy wrappers; avoid double-registration issues (same ID).
4. Add tests that:
   - import only `StageRegistry` / `QuantSDK` (not `scripts/*`)
   - verify `StageRegistry.get_stage("meta.returns")` succeeds
   - verify `scripts/quant_cli.py stage list --category meta` prints expected entries (can be tested via subprocess if existing test patterns support it).

## Acceptance Criteria

1. **Deterministic Stage Discovery**
   - Given a fresh Python process
   - When importing `tradingview_scraper.orchestration.registry.StageRegistry` and listing stages
   - Then `meta.returns`, `meta.optimize`, `meta.flatten`, and `meta.report` appear without requiring imports from `scripts/*`.

2. **Stable Invocation**
   - Given the meta stages are registered
   - When calling `QuantSDK.run_stage("meta.returns", ...)` with valid parameters
   - Then the stage callable is resolved and executed (mocked execution is acceptable for this task; functional correctness of each stage is handled in later tasks).

3. **Backwards Compatibility**
   - Given existing scripts like `scripts/run_meta_pipeline.py`
   - When running them after this change
   - Then they continue to work (no import errors, no stage ID collisions that break registry lookups).

4. **Unit Test Coverage**
   - Given the new registration mechanism
   - When running the test suite
   - Then there are unit tests verifying stage registration and lookup behavior for meta stages.

## Metadata
- **Complexity**: Medium
- **Labels**: Meta, Orchestration, StageRegistry, SDK, Determinism
- **Required Skills**: Python packaging/imports, test design, orchestration patterns

