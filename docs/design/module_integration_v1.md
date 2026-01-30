# Design: Module Integration & Verification (Phases 325-327)

This document specifies the integration strategy for the newly modularized components (Filters, Discovery, Meta-Portfolio) into the production pipeline.

## 1. Phase 325: Filter Integration (Selection Policy)

### Objective
Replace the hardcoded `_apply_vetoes` logic in `SelectionPolicyStage` with a pluggable filter chain using the classes in `tradingview_scraper/pipelines/selection/filters/`.

### SDD (Specification)
- `SelectionPolicyStage` will accept an optional `filters: List[BaseFilter]` argument in its constructor.
- If no filters are provided, it will default to a standard chain: `[DarwinianFilter(), SpectralFilter(), FrictionFilter()]`.
- The `execute` method will iterate through the filter chain, calling `apply(context)` on each.
- Vetoed symbols from all filters will be aggregated into a single `disqualified` set.
- All filter-specific logging will be handled by the filters themselves via `context.log_event`.

### TDD (Test Plan)
- `tests/test_selection_filters.py`:
    - Test each filter in isolation with mock `SelectionContext`.
    - `DarwinianFilter`: Assert veto on missing `tick_size`.
    - `SpectralFilter`: Assert veto on `entropy > threshold`.
    - `FrictionFilter`: Assert veto on `eci > hurdle`.
- `tests/test_policy_integration.py`:
    - Instantiate `SelectionPolicyStage` with a custom filter list.
    - Verify that `execute` correctly identifies disqualified assets from all filters in the list.

## 2. Phase 326: Discovery Integration

### Objective
Standardize asset discovery by using the `DiscoveryPipeline` and `BaseDiscoveryScanner` abstractions in the main execution scripts.

### SDD (Specification)
- `scripts/compose_pipeline.py` will be refactored to use `DiscoveryPipeline.run_profile(profile_name)`.
- The `TradingViewDiscoveryScanner` will be the primary implementation.
- Standardized `CandidateMetadata` will be converted to the legacy dict format for downstream compatibility during the transition period.

### TDD (Test Plan)
- `tests/test_discovery_integration.py`:
    - Mock `FuturesUniverseSelector.run` to return a controlled set of rows.
    - Assert `DiscoveryPipeline.run_profile` returns the expected `CandidateMetadata` objects.
    - Verify that `logic` metadata from manifest "strategies" is correctly injected.

## 3. Phase 327: Meta-Portfolio Integration

### Objective
Modernize the Meta-Portfolio pipeline (`run_meta_pipeline.py`) using `MetaContext`, `SleeveAggregator`, and `WeightFlattener`.

### SDD (Specification)
- `scripts/run_meta_pipeline.py` will initialize a `MetaContext`.
- `SleeveAggregator` will be used to build `meta_returns` in Stage 1.
- `WeightFlattener` will be used to project optimized weights in Stage 3.
- The pipeline will remain functionally identical to the current implementation but with cleaner, testable building blocks.

### TDD (Test Plan)
- `tests/test_meta_integration.py`:
    - Create mock sleeve returns and weights.
    - Verify `SleeveAggregator.aggregate` handles index alignment and UTC normalization.
    - Verify `WeightFlattener.flatten` handles net weight calculation and sleeve labeling.

## 4. Non-Functional Requirements (Deferred)
- Ray Native Actors for Discovery/Sleeves (Phase 345).
- Prefect Workflow definitions (Phase 350).
- Claude Skill script optimization (Phase 355 - Refinement).
