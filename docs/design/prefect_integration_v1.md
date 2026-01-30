# Design: Prefect Workflow Integration (Phase 350)

This document specifies the integration of Prefect 3.x to provide robust DAG management, retries, and observability for the quantitative pipeline.

## 1. Objective
Wrap the addressable stages (Phase 340) and Ray compute tasks (Phase 345) into formal Prefect Flows. This replaces the imperative `run_production_pipeline.py` sequences with declarative, recoverable workflows.

## 2. Architecture

```python
@flow(name="Selection Flow")
def selection_flow(profile: str, run_id: str):
    # Tasks wrap QuantSDK.run_stage calls
    ctx = task_ingest(profile, run_id)
    ctx = task_features(ctx)
    ctx = task_inference(ctx)
    # ...
```

### 2.1 Task Granularity
Each `BasePipelineStage` corresponds to one Prefect `@task`.
- **Retries**: Network-bound stages (Ingestion, Synthesis) get `retries=3`.
- **Caching**: Compute-bound stages (Features, Inference) get `cache_key_fn=task_input_hash`.

### 2.2 Ray Integration (`prefect-ray`)
We will use the `RayTaskRunner` to execute Prefect tasks on the existing Ray cluster.

```python
from prefect_ray import RayTaskRunner

@flow(task_runner=RayTaskRunner())
def meta_portfolio_flow():
    # These tasks run in parallel on Ray workers
    futures = [run_sleeve_task.submit(p) for p in profiles]
```

## 3. Implementation Plan

### 3.1 `tradingview_scraper/orchestration/flows/selection.py`
Defines `run_selection_flow(profile, run_id)`.
- Replaces logic in `scripts/run_production_pipeline.py`.

### 3.2 `tradingview_scraper/orchestration/flows/meta.py`
Defines `run_meta_flow(meta_profile)`.
- Replaces logic in `scripts/run_meta_pipeline.py`.
- Manages the "Scatter-Gather" pattern for sleeves.

## 4. TDD Strategy (`tests/test_prefect_integration.py`)
- **Mock Prefect**: Use `prefect_test_harness` to run flows locally without a server.
- **Verify Graph**: Assert that tasks are called in the correct topological order.
- **Verify Recovery**: Simulate a task failure and verify retry behavior (mocked).

## 5. Deployment
- **Local**: `prefect flow serve` for development.
- **Production**: Dockerized deployment (Phase 360).
