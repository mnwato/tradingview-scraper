---
status: pending
created: 2026-01-21
started: null
completed: null
---
# Task: Unify Meta Pipeline Orchestration (Scripts + ProductionPipeline)

## Description
Unify the meta-portfolio orchestration so that there is a single canonical meta pipeline execution path used by:
1) `scripts/run_meta_pipeline.py` (direct meta runs), and
2) the meta branch inside `scripts/run_production_pipeline.py` (when a profile is meta).

This prevents drift where one orchestrator runs build+optimize+report while another omits flattening or uses different paths/flags.

## Background
The repo has multiple orchestration surfaces:
- `scripts/run_meta_pipeline.py` (standalone meta flow)
- meta steps embedded inside `scripts/run_production_pipeline.py` (production flow that branches for meta profiles)
- `Makefile` target `flow-meta-production` (calls `scripts/run_meta_pipeline.py`)

Today, `scripts/run_meta_pipeline.py` calls `QuantSDK.run_stage("meta.*")` for all steps, while `scripts/run_production_pipeline.py` has its own meta-step list and currently omits flattening.

## Reference Documentation
**Required:**
- Design: docs/specs/multi_sleeve_meta_portfolio_v1.md

**Additional References (if relevant to this task):**
- docs/specs/fractal_meta_portfolio_v1.md (stage sequence)
- docs/design/orchestration_layer_v1.md (addressable stages)

**Note:** You MUST read the detailed design document before beginning implementation. Read additional references as needed for context.

## Technical Requirements
1. Define a single canonical meta pipeline runner (e.g., `MetaPipeline.execute()`), which:
   - runs stages in the correct order: returns → optimize → flatten → report
   - supports `--execute-sleeves` parallel execution (Ray) when requested
   - writes artifacts into the active run directory
2. Update `scripts/run_meta_pipeline.py` to delegate to the canonical runner (no duplicated stage calls).
3. Update `scripts/run_production_pipeline.py` meta branch to delegate to the canonical runner and include flattening for at least the configured risk profiles.
4. Ensure meta pipeline uses the manifest’s sleeve list and meta allocation constraints (`min_weight`, `max_weight`) where applicable.
5. Ensure CLI ergonomics:
   - `make flow-meta-production PROFILE=<meta_profile>` remains a supported entrypoint.
6. Add tests that assert meta orchestration runs the full stage set in order (can be mock-based).

## Dependencies
- `scripts/run_meta_pipeline.py`
- `scripts/run_production_pipeline.py`
- `tradingview_scraper/orchestration/sdk.py` and meta stage implementations from Task 02
- `tradingview_scraper/orchestration/compute.py` and `sleeve_executor.py` for Ray parallel sleeves

## Implementation Approach
1. Implement `MetaPipeline` in package code (preferred) or in scripts if the repo pattern dictates, but keep business logic in the package.
2. Ensure the canonical runner accepts:
   - `meta_profile`
   - `profiles` (risk profiles list)
   - `execute_sleeves` boolean
   - `run_id` (explicit or generated)
3. Replace embedded meta step lists in `scripts/run_production_pipeline.py` with a single call.
4. Add a test verifying call ordering:
   - if `execute_sleeves=True`, Ray execution occurs before `meta.returns`
   - stages are called in order and abort on sleeve failures

## Acceptance Criteria

1. **Single Canonical Execution Path**
   - Given `scripts/run_meta_pipeline.py` and `scripts/run_production_pipeline.py`
   - When running meta profiles through either entrypoint
   - Then they execute the same canonical pipeline sequence and produce the same set of artifacts (up to run_id differences).

2. **Flattening Included**
   - Given a meta pipeline run completes successfully
   - When inspecting the run directory outputs
   - Then a flattened meta portfolio artifact exists for each configured risk profile (or at minimum a clearly documented primary profile).

3. **Parallel Sleeve Execution Support**
   - Given `--execute-sleeves` is enabled and sleeves require execution
   - When the pipeline is run
   - Then sleeves are executed in parallel via Ray and failures abort the meta pipeline before meta optimization.

4. **Unit/Integration Tests**
   - Given the orchestration changes
   - When running the test suite
   - Then tests exist verifying ordering and inclusion of all stages.

## Metadata
- **Complexity**: Medium
- **Labels**: Meta, Orchestration, Ray, ProductionPipeline, Refactor
- **Required Skills**: Python refactoring, orchestration patterns, test doubles/mocking

