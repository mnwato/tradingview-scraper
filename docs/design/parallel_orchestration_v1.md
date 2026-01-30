# Design Specification: Multi-Sleeve Parallelization with Ray (v2.0)

## 1. Problem Statement
The current meta-portfolio production flow executes atomic sleeves sequentially. To achieve institutional throughput, we must parallelize sleeve execution. Leveraging **Ray** allows us to avoid reinventing process management, providing robust task distribution, dashboard visibility, and future cluster scalability.

## 2. Proposed Architecture

### 2.1 Ray Orchestrator
- **Mechanism**: Utilize `ray.remote` tasks for individual sleeve production.
- **Resource Constraints**: Each sleeve task will be tagged with `num_cpus` and `memory` requirements to prevent system thrashing.
- **Dashboard**: Enable Ray Dashboard (default port 8265) for real-time monitoring of sleeve execution.

### 2.2 Shared Resources & Safety
- **State Management**: Ray's Object Store will be used to pass configuration contexts.
- **File Locking**: Retain `filelock` for physical disk writes (e.g., `selection_audit.json`).
- **Isolation**: Each sleeve run creates a unique `RUN_ID`, ensuring workspace isolation.

### 2.3 Integration Path
1. **Ray Initialization**: `ray.init(ignore_reinit_error=True)` at the start of `run_meta_pipeline.py`.
2. **Task Wrapper**: Create a `run_sleeve_task.remote()` function that encapsulates the logic currently in `make flow-production`.
3. **Wait & Aggregate**: Use `ray.get()` to block until all sleeves are complete before entering the fractal aggregation stage.

## 3. Implementation Plan
1. **Task 223.1**: Implement `scripts/parallel_orchestrator_ray.py`.
2. **Task 223.2**: Refactor `run_meta_pipeline.py` to use Ray tasks.
3. **Task 223.3**: Validate scaling performance on `meta_benchmark` (Target: > 60% reduction in wall-clock time).
