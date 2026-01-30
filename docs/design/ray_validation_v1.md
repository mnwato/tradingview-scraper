# Design: Ray Integration Validation (Phase 346)

This document specifies the validation strategy for the Ray Compute Layer within the context of full Meta-Portfolio pipelines.

## 1. Objective
Verify that the `meta_benchmark` and `meta_ma_benchmark` profiles correctly utilize the `RayComputeEngine` for parallel sleeve execution when required. Ensure the orchestration flow from dispatch to reporting is unbroken.

## 2. Target Profiles

| Meta Profile | Sleeves | Expected Strategy |
| :--- | :--- | :--- |
| `meta_benchmark` | `binance_spot_rating_all_long`, `binance_spot_rating_all_short` | Composite (All) |
| `meta_ma_benchmark` | `binance_spot_rating_ma_long`, `binance_spot_rating_ma_short` | Trend (MA) |

## 3. Validation Logic (SDD)

### 3.1 Dispatch Trigger
The `run_meta_pipeline.py` script triggers Ray execution if:
1. `--execute-sleeves` is passed.
2. The `run_id` for a sleeve in `manifest.json` is missing or contains the string "baseline".

### 3.2 Mock-Based Integration Testing
To avoid long-running compute during validation, we will:
- Patch `configs/manifest.json` to remove static `run_id` values for the test profiles.
- Mock `RayComputeEngine.execute_sleeves` to return success immediately.
- Mock the file-heavy post-processing steps (`build_meta_returns`, `optimize_meta`, `flatten_weights`, `generate_meta_markdown_report`).

## 4. Test Specification (TDD)

### 4.1 `tests/integration/test_ray_meta_orchestration.py`

- **Test Case 1: `test_meta_benchmark_ray_dispatch`**
    - **Setup**: Provide a manifest where `meta_benchmark` sleeves have no `run_id`.
    - **Action**: Call `run_meta_pipeline("meta_benchmark", execute_sleeves=True)`.
    - **Assert**: `RayComputeEngine.execute_sleeves` was called with exactly 2 sleeves: `all_long` and `all_short`.

- **Test Case 2: `test_meta_ma_benchmark_ray_dispatch`**
    - **Setup**: Provide a manifest where `meta_ma_benchmark` sleeves have no `run_id`.
    - **Action**: Call `run_meta_pipeline("meta_ma_benchmark", execute_sleeves=True)`.
    - **Assert**: `RayComputeEngine.execute_sleeves` was called with exactly 2 sleeves: `ma_long` and `ma_short`.

- **Test Case 3: `test_full_orchestration_sequence`**
    - **Assert**: The order of calls is `execute_sleeves` -> `build_meta_returns` -> `optimize_meta` -> `flatten_weights` -> `generate_meta_markdown_report`.

## 5. Success Criteria
- [ ] Dispatcher correctly identifies sleeves needing execution.
- [ ] Ray engine is initialized only when sleeves need execution.
- [ ] MetaContext is correctly propagated.
- [ ] All integration tests pass.
