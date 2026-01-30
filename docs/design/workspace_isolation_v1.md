# Design: Workspace Isolation V1 (Virtual Workspaces)

## 1. Problem Statement
In the multi-sleeve meta-portfolio architecture, multiple production pipelines run concurrently (via Ray).
- **Conflict Risk**: If multiple pipelines attempt to write to shared resources (e.g., `data/lakehouse/*.parquet` or global logs), race conditions occur, leading to data corruption.
- **Candidate Contamination**: If a pipeline fails to generate its own `portfolio_candidates.json` and falls back to reading the shared `data/lakehouse/portfolio_candidates.json`, it may optimize on the wrong universe (cross-contamination).
- **Configuration Leakage**: Global singleton settings (`TradingViewScraperSettings`) might bleed between threads if not properly isolated.

## 2. Solution: The "Virtual Workspace" Model
We achieve isolation without heavy containerization (Docker) by using **Process-Level Boundaries** enforced by Ray Actors, combined with **Namespace Conventions**.

### 2.1 Process Isolation (Memory)
- **Mechanism**: Each Ray Actor (`SleeveProductionActor`) is a separate OS process.
- **Benefit**:
    - `sys.modules` is unique per actor.
    - `os.environ` is unique per actor.
    - `TradingViewScraperSettings` singleton is instantiated freshly in each process, preventing config bleed.

### 2.2 Filesystem Isolation (Storage)
We distinguish between **Shared Read-Only** and **Isolated Write-Only** paths.

#### A. Shared Read-Only Layer (The Lakehouse)
- **Path**: `data/lakehouse/`
- **Role**: Source of Truth for raw market data (`OHLCV`).
- **Constraint**: Parallel sleeves MUST NOT write to the Lakehouse.
- **Enforcement**:
    - Set `PORTFOLIO_DATA_SOURCE=lakehouse_only` for all Ray Actors.
    - This forces `scripts/prepare_portfolio_data.py` to skip `sync()`/`repair()` calls, preventing concurrent writes to `*.parquet` files.
    - **Pre-requisite**: A single, serial `make flow-data` or `make data-ingest` must run *before* the parallel phase to ensure the Lakehouse is fresh.

#### B. Isolated Write-Only Layer (The Run Directory)
- **Path**: `artifacts/summaries/runs/<TV_RUN_ID>/`
- **Role**: Scratchpad and Artifact storage for the specific pipeline execution.
- **Mechanism**:
    - Every sleeve is assigned a unique `TV_RUN_ID` (e.g., `ray_long_ma_20260119...`).
    - The `ProductionPipeline` class initializes its workspace (`self.run_dir`) based on this ID.
    - All intermediate files (`returns_matrix.parquet`, `portfolio_candidates.json`) and final reports are written here.

#### C. Strict Candidate Isolation
- **Risk**: Default behavior in `prepare_portfolio_data.py` falls back to `data/lakehouse/portfolio_candidates.json` if the run-specific file is missing.
- **Mitigation**:
    - Introduce `TV_STRICT_ISOLATION=1` env var.
    - If set, `prepare_portfolio_data.py` MUST fail if `CANDIDATES_SELECTED` (Run Dir) is missing, rather than falling back to Lakehouse.

## 3. Implementation Plan (Phase 234)

### 3.1 Update Orchestrator
Modify `scripts/parallel_orchestrator_native.py` to inject safety flags:
```python
env_vars["PORTFOLIO_DATA_SOURCE"] = "lakehouse_only"
env_vars["TV_STRICT_HEALTH"] = "1"  # Fail fast if Lakehouse data is missing
env_vars["TV_STRICT_ISOLATION"] = "1" # Prevent candidate fallback
```

### 3.2 Update `prepare_portfolio_data.py`
Add logic to check `TV_STRICT_ISOLATION` and abort if local candidates are missing.

## 4. Verification
- **Test**: Run `meta_ray_test` (which uses Native Ray) and verify logs show:
    - `PORTFOLIO_DATA_SOURCE=lakehouse_only: Skipping network ingestion.`
    - Candidates loaded from `artifacts/summaries/runs/.../portfolio_candidates.json`.
    - No modification times changed in `data/lakehouse`.
