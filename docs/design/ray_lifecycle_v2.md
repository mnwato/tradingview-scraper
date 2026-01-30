# Design: Ray Lifecycle & Resource Resilience (v2)

## 1. Objective
To ensure deterministic initialization, resource-aware execution, and graceful termination of the Ray compute cluster.

## 2. Lifecycle Management

### 2.1 The Context Manager Pattern
`RayComputeEngine` will implement the `__enter__` and `__exit__` dunder methods to formalize the cluster lifecycle.

```python
with RayComputeEngine() as engine:
    results = engine.execute_sleeves(sleeves)
# ray.shutdown() called automatically in __exit__
```

### 2.2 Re-initialization Safety
`ray.init()` will be called with `ignore_reinit_error=True` and a check for `ray.is_initialized()`. 

## 3. Resource Awareness

### 3.1 Dynamic Capping
The engine will prioritize resource limits in the following order:
1.  **Environment Variables**: `TV_ORCH_CPUS`, `TV_ORCH_MEM_GB`.
2.  **Explicit Constructor Params**: `num_cpus`, `memory_limit`.
3.  **Heuristic Defaults**: `min(2, os.cpu_count())` for safe local execution.

### 3.2 Object Spilling
Enable `object_spilling_threshold=0.8` to prevent cluster-wide OOM during large-scale return matrix aggregations.

## 4. Graceful Shutdown

### 4.1 Signal Handling
The orchestrator will register a `signal.SIGINT` (Ctrl+C) handler to ensure:
1.  All active Ray Actors are killed.
2.  `ray.shutdown()` is invoked.
3.  Audit ledger records the "Aborted" status.

### 4.2 Actor Cleanup
`SleeveActorImpl` will provide a `cleanup()` method to:
1.  Close any open file handles.
2.  Finalize the local audit ledger.
3.  Export remaining logs before the process is terminated.

## 5. Process Isolation (Workspace)
- **Shared Inputs**: `data/lakehouse` and `data/export` are SYMLINKED to the host filesystem.
- **Isolated Outputs**: `data/artifacts` and `data/logs` are LOCAL to the worker and explicitly EXPORTED (copied) to the host upon successful pipeline completion.
