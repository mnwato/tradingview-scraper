# Design: Ray Native Migration (v1)

## 1. Context
Currently, `scripts/parallel_orchestrator_ray.py` executes production sleeves by spawning subprocesses (`subprocess.run`) that call `uv run ...`. This ensures environment isolation and consistency with the CLI workflow but incurs overhead:
- **Process Overhead**: New Python interpreter and dependency resolution for every task.
- **Serialization**: Inputs/outputs are passed via CLI args and disk (JSON/Parquet), not shared memory.
- **Opacity**: Ray dashboard sees only a generic "shell command" task, not granular progress or metrics.

## 2. Goals
- **Native Execution**: Import `scripts.run_production_pipeline` directly in the Ray worker.
- **Shared Memory**: Use Ray's object store for intermediate data (if applicable in future).
- **Observability**: Expose granular steps (Selection, Optimization) as Ray tasks or progress reports.

## 3. Challenges
- **Dependency Management**: The host environment (where `ray` runs) must have all dependencies installed that the pipeline needs. `uv` handles this for us in the subprocess model. In native mode, we must ensure the Ray worker environment matches `pyproject.toml`.
- **Global State**: `tradingview_scraper.settings` is a singleton. Parallel runs in the *same* process (threads) would clash. Ray uses *processes* (workers), so singletons are isolated per worker, which is safe.
- **Working Directory**: The pipeline relies on `os.getcwd()` being the project root for file paths. Ray workers might run in a sandbox.

## 4. Migration Strategy

### Phase A: Class-Based Actor Wrapper (Immediate)
Wrap the existing `ProductionPipeline` class in a Ray Actor.

```python
@ray.remote
class SleeveActor:
    def run(self, profile: str, run_id: str):
        # 1. Setup Env (Chdir to project root if needed)
        os.chdir(os.getenv("RAY_HOST_CWD"))
        
        # 2. Instantiate Pipeline
        from scripts.run_production_pipeline import ProductionPipeline
        pipeline = ProductionPipeline(profile=profile, run_id=run_id)
        
        # 3. Execute
        pipeline.execute()
        return {"status": "success"}
```

### Phase B: Runtime Environment (Robustness)
Use Ray's `runtime_env` to ensure dependencies are present.
```python
ray.init(runtime_env={"working_dir": ".", "pip": ["./pyproject.toml"]}) 
# Or rely on the fact we are running local mode for now.
```

### Phase C: Granular Task Graph (Future)
Break `pipeline.execute()` into distinct Ray tasks:
- `ingest_data.remote()`
- `optimize_portfolio.remote()`
This allows finer-grained retries and parallelism *within* a sleeve.

## 5. Execution Plan (Phase 232)
1.  **Refactor**: Modify `ProductionPipeline` to be more import-friendly (reduce global side effects on import).
2.  **Prototype**: Create `scripts/parallel_orchestrator_native.py` that imports `ProductionPipeline`.
3.  **Test**: Run a single sleeve (`meta_ray_test`) using the native orchestrator.
4.  **Compare**: Measure overhead reduction vs subprocess approach.
