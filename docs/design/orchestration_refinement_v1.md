# Design: SDK-Driven Meta Orchestration (Phase 347)

This document specifies the refinement of the meta-portfolio pipeline to fully leverage the `QuantSDK` and `StageRegistry` established in Phase 340.

## 1. Objective
Transition the imperative logic in `run_meta_pipeline.py` into a series of addressable stages registered in the `StageRegistry`. This enables better observability, modular testing, and future Prefect integration.

## 2. Stage Registration

The following functions will be wrapped/decorated as addressable stages:

| Stage ID | Implementation | Purpose |
| :--- | :--- | :--- |
| `meta.returns` | `scripts.build_meta_returns` | Aggregate sleeve returns |
| `meta.optimize` | `scripts.optimize_meta_portfolio` | Solve for meta-weights |
| `meta.flatten` | `scripts.flatten_meta_weights` | Project to asset weights |
| `meta.report` | `scripts.generate_meta_report` | Forensic reporting |

## 3. MetaContext Lifecycle

The `MetaContext` will be the primary state container:
1. **Initialize**: At the start of `run_meta_pipeline`.
2. **Sleeve Generation**: Populate `sleeve_profiles` and trigger Ray if needed.
3. **Aggregation**: `meta.returns` populates `meta_returns`.
4. **Optimization**: `meta.optimize` populates `meta_weights`.
5. **Flattening**: `meta.flatten` populates `flattened_weights`.

## 4. SDK Integration (SDD)

Refactor `run_meta_pipeline.py` to:
```python
# Before
build_meta_returns(...)

# After
QuantSDK.run_stage("meta.returns", context=meta_context, **params)
```

## 5. TDD Plan

### 5.1 `tests/integration/test_sdk_meta_flow.py`
- **Assertion**: Verify that calling the SDK with "meta.full" (to be implemented) or individual meta stages correctly updates the `MetaContext`.
- **Mocking**: Reuse mocks from Phase 346 for file I/O.

## 7. Phase 348: Orchestration Hardening (Strict Success Gate)

### Objective
Ensure that the meta-portfolio pipeline is resilient to partial failures in distributed sleeve execution.

### SDD (Specification)
- **Stop-the-Line Logic**: The `run_meta_pipeline` function must verify the status of every sleeve dispatched to Ray.
- **Abort Condition**: If any sleeve returns a status other than `"success"`, the pipeline must raise a `RuntimeError` and terminate immediately.
- **Reporting**: The error message must clearly list which sleeve(s) failed and provide their respective error messages from the Ray Actor.

### TDD (Integration Test)
- **Test Case**: `test_meta_pipeline_aborts_on_sleeve_failure`
- **Mock**: Configure `RayComputeEngine.execute_sleeves` to return one success and one failure.
- **Expectation**: `run_meta_pipeline` raises `RuntimeError`.
