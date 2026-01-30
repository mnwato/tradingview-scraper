# Design: Ray Compute Layer (Phase 345)

This document specifies the architecture for the **Ray Compute Layer**, which provides parallel execution capabilities for full strategy sleeves.

## 1. Objective
Replace ad-hoc Ray scripts with a formalized `RayComputeEngine` and `SleeveActor` that integrate with the `QuantSDK` patterns. This enables parallel execution of strategy sleeves with resource isolation and artifact persistence.

## 2. Architecture

### 2.1 The Compute Engine (`tradingview_scraper/orchestration/compute.py`)
A central manager for the Ray cluster and task dispatch.

```python
class RayComputeEngine:
    def __init__(self, num_cpus: int = None, memory_limit: int = None):
        self.num_cpus = num_cpus
        self.memory_limit = memory_limit

    def ensure_initialized(self):
        if not ray.is_initialized():
            ray.init(num_cpus=self.num_cpus, ignore_reinit_error=True)

    def execute_sleeves(self, sleeves: List[Dict[str, str]]) -> List[Dict]:
        """
        Run multiple sleeves in parallel using Native Actors.
        Args:
            sleeves: List of {"profile": "...", "run_id": "..."}
        """
        self.ensure_initialized()
        host_cwd = os.getcwd()
        env_vars = self._capture_env()
        
        # Spawn one actor per sleeve
        actors = [SleeveActor.remote(host_cwd, env_vars) for _ in sleeves]
        
        # Dispatch
        futures = [a.run_pipeline.remote(s["profile"], s["run_id"]) for a, s in zip(actors, sleeves)]
        results = ray.get(futures)
        
        # Cleanup
        for a in actors:
            ray.kill(a)
            
        return results

    def _capture_env(self) -> Dict[str, str]:
        return {k: v for k, v in os.environ.items() if k.startswith("TV_") or k in ["PYTHONPATH", "PATH"]}
```

### 2.2 The Sleeve Actor (`tradingview_scraper/orchestration/sleeve_executor.py`)
A stateful Ray Actor that encapsulates the `ProductionPipeline` execution.

- **Isolation**: Each actor has its own process. It symlinks the shared `data/lakehouse` but uses local `data/artifacts` and `data/logs` to prevent write collisions.
- **Artifact Export**: After execution, it zips and copies its local artifacts back to the host filesystem.
- **Interface**:
    ```python
    @ray.remote(num_cpus=1, memory=3 * 1024 * 1024 * 1024)
    class SleeveActor:
        def __init__(self, host_cwd: str, env_vars: Dict[str, str]):
            # Setup environment and isolation symlinks
            pass

        def run_pipeline(self, profile: str, run_id: str) -> Dict:
            # Execute ProductionPipeline and export artifacts
            pass
    ```

## 3. Integration Plan

1.  **Refactor `scripts/run_meta_pipeline.py`**:
    - Replace `execute_parallel_sleeves` (subprocess) with `RayComputeEngine.execute_sleeves()`.
2.  **Standardize Resources**:
    - Default to 1 CPU and 3GB RAM per sleeve actor.
3.  **Path Stability**:
    - Ensure all paths use the root-relative pattern established in the platform.

## 4. TDD Plan (`tests/test_ray_compute.py`)

- **Mock Ray**: Use `unittest.mock` to mock `ray.init`, `ray.get`, and the `.remote()` calls.
- **Assertions**:
    - `test_engine_init`: Assert `ray.init` is called.
    - `test_dispatch_logic`: Assert correct number of actors are spawned and tasks dispatched.
    - `test_actor_init`: Assert actor sets up symlinks and env vars.
