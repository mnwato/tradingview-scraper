# Specification: MLOps Scalability & Orchestration (v1)

## 1. Objective
To transition the platform from a "manual plumbing" state to an institutional-grade MLOps architecture. This shift allows the research team to focus exclusively on **Alpha Core** development (Strategy, Risk, Selection) while the infrastructure handles scalability, durability, and distributed compute.

## 2. The Tech Stack (The "Scale Pivot")

### 2.1 Compute Engine: Ray Core
- **Role**: High-performance task execution and memory sharing.
- **Key Feature**: **Shared Object Store**. Avoids the 16Gi RAM bottleneck by storing large returns matrices in shared memory, accessible by all workers without duplication.
- **Abstraction**: Every "Backtest Window" is a Ray Remote Task.

### 2.2 Workflow Orchestrator: Prefect
- **Role**: Durable state management and observability.
- **Key Feature**: **Task Caching & Resumability**. Every backtest unit is uniquely hashed. Results are persisted in a local SQL-backed state store. 
- **Efficiency**: Rerunning a 1,000-config tournament after a minor code change results in 99% cache hits, executing only the affected delta.

### 2.3 Infrastructure Orchestrator: SkyPilot
- **Role**: Cloud Bursting.
- **Standard**: Define `tournament.yaml` for SkyPilot to automatically provision high-memory instances (e.g., AWS `r6i.4xlarge`) for large-scale "5D" sweeps.

## 3. Structural Design: Task Atomicity

To support this stack, all backtest logic must be refactored into **Pure Tasks**:

```python
@task
@ray.remote
def run_backtest_unit(weights, returns, simulator_params):
    # Pure logic: Inputs -> Simulator -> Metrics
    return metrics
```

## 4. Benefit Realization

| Dimension | Legacy (Manual) | Scalable (MLOps) | Impact |
| :--- | :--- | :--- | :--- |
| **Development** | Re-writing loop logic | Decorating alpha functions | **Focus on Strategy** |
| **Data Scaling** | Limited by 16Gi RAM | Shared Memory (Plasma) | **10x Data Depth** |
| **Iterative Speed**| Full reruns required | Native Task Caching | **100x Iteration Speed** |
| **Auditability** | Grepping text logs | Queryable Task DB | **Forensic Integrity** |

## 5. Implementation Phases

1. **Refactor (Taskification)**: Decouple `BacktestEngine` into atomized tasks.
2. **Compute Integration**: Implement Ray for the 4D tournament loop.
3. **Orchestration Integration**: Implement Prefect for state and caching.
4. **Cloud Hook**: Implement SkyPilot for burst compute.
