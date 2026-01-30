# Specification: Performance Tuning & Concurrency (v1)

## 1. Objective
To maximize quantitative research velocity by optimizing the 4D tournament execution path. This spec targets a 10x speedup through architectural decoupling and process-level parallelism.

## 2. Architectural Decoupling: The "Weights Cube"

The primary bottleneck in large-scale tournaments is the redundant execution of optimization solvers.

### Legacy Flow (Sequential)
`For Rebalance -> For Selection -> For Engine -> For Profile -> [Optimize -> For Simulator -> Simulate]`
- **Inefficiency**: Solvers are re-run for every simulator, even though target weights are identical.

### Optimized Flow (Two-Stage)
1. **Stage 1 (Weight Generation)**:
   - Run solvers for all (Selection, Engine, Profile) combinations across all windows.
   - Cache results in a structured `weights_cube.pkl`.
2. **Stage 2 (Parallel Simulation)**:
   - Feed the `weights_cube` into a pool of parallel simulator workers.
   - Each worker handles a unique (Rebalance, Simulator) combination.

## 3. Concurrency & Orchestration Standards

### 3.1 Distributed Compute: Ray Core
- **Tool**: `ray` (replacing `ProcessPoolExecutor`).
- **Object Store**: Use Ray's shared memory (Plasma) to store the 500-day returns matrix and `weights_cube`. This ensures zero-copy data sharing across workers, critical for 16Gi RAM environments.
- **Scaling**: Standardized on `.remote()` task execution to allow seamless transitions from local multicore to cloud clusters via **SkyPilot**.

### 3.2 Durable Execution: Prefect
- **Tool**: `prefect` (Orchestration & State).
- **Caching**: Decorate backtest tasks with `@task(cache_key_fn=...)`. This ensures that rerunning a tournament with a modified selection mode only executes the changed tasks, skipping identical cached windows.
- **Visibility**: Leverage the Prefect UI for real-time monitoring of combinatorial backtests, replacing manual grep-based log audits.

## 4. Fidelity Tiers

Researchers can trade fidelity for speed using the `--fidelity` flag:

| Tier | Simulators Included | Use Case |
| :--- | :--- | :--- |
| **`low`** | `custom` | Instant alpha exploration and logic debugging. |
| **`medium`**| `custom`, `vectorbt` | Rapid friction and rebalance drift analysis. |
| **`high`** | `custom`, `vectorbt`, `cvxportfolio`, `nautilus` | Institutional audit and final production validation. |

## 5. Implementation Roadmap

1. **Decouple `BacktestEngine`**: Extract weight computation logic into a standalone generator.
2. **Update `Grand4DTournament`**: Implement the two-stage execution and worker pool.
3. **Resumable State**: Implement a `tournament_state.json` to allow resumption of interrupted runs.
