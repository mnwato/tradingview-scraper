# Design: Workspace Isolation & Artifact Consolidation (Phase 235)

## 1. Context & Problem
In the Ray Native architecture (Phase 234), workers execute in an isolated `runtime_env`. However, legacy scripts were designed assuming a **Shared Filesystem** where multiple processes read/write to `data/lakehouse` or `export/`.

When running under Ray Native:
1.  **Read Violations**: Scripts try to read from `export/` or `data/lakehouse` (which are symlinked/excluded/missing).
2.  **Write Violations**: Scripts try to write to these shared paths. If `data` is a symlink to the host, this corrupts the host state or fails if read-only.
3.  **Artifact Scattering**: Intermediate files are scattered across `data/`, `export/`, and `artifacts/`, making atomic export difficult.

## 2. The Standard: Run-Local Artifacts (REQ-ISO-004)
To ensure isolation and atomic export, **ALL** intermediate and final outputs of a pipeline run MUST be written to `TV_RUN_DIR` (mapped to `artifacts/summaries/runs/<RUN_ID>`).

### 2.1 Directory Structure
Inside the isolated worker:
```
./
  artifacts/
    summaries/
      runs/
        <RUN_ID>/
          data/           <-- ALL intermediate data (candidates, returns, logs)
          reports/        <-- Final reports
          config/         <-- Resolved manifest
```

### 2.2 Environment Variables
The `ProductionPipeline` already sets these, but scripts must be audited to respect them:
- `TV_RUN_DIR`: Root of the run artifacts.
- `CANDIDATES_RAW`: Input candidates (from scans).
- `CANDIDATES_SELECTED`: Filtered candidates.
- `SELECTION_AUDIT`: Audit log.

## 3. Audit Findings (Phase 235)
### `scripts/select_top_universe.py`
- **Issue**: Hardcoded `AUDIT_FILE = "data/lakehouse/selection_audit.json"`.
- **Issue**: Resolves input export dir using `Path("export")` which might be missing in isolation if not symlinked or if scans haven't run in this session.
- **Fix**: 
    - Respect `SELECTION_AUDIT` env var.
    - Accept an explicit `--scan-dir` argument or env var to locate scanner outputs (which should be provided/symlinked).

### `data/lakehouse` Dependency
- The `parallel_orchestrator_native.py` symlinks the host `data/` to worker `data/`.
- **Risk**: If a script writes to `data/lakehouse/...`, it modifies the HOST.
- **Mitigation**: Scripts running in production mode (`TV_PROFILE!=development`) must treat `data/lakehouse` as **Read-Only**.

## 4. Implementation Plan
1.  **Refactor `select_top_universe.py`**:
    - Use `os.getenv("SELECTION_AUDIT")` instead of hardcoded path.
    - Ensure input search path is configurable (`TV_SCAN_DIR`?).
    
2.  **Update `parallel_orchestrator_native.py`**:
    - Symlink `export` directory (Read-Only?) if needed for `select_top_universe.py` to find scanner results. 
    - **Crucial**: Scanners usually run *before* the pipeline. In `meta_ray_test`, we skip scanning. So where does `select_top_universe` find input?
    - *Answer*: It looks in `export/`. If `meta_ray_test` doesn't have scans, it finds nothing -> empty universe -> crash/failure.
    - **Fix for Test**: `meta_ray_test` skips discovery. `data-prep-raw` calls `select_top_universe`. If no files in `export/`, it returns empty.
    
3.  **Consolidation**:
    - `prepare_portfolio_data.py` must write to `TV_RUN_DIR/data`. (Already does via env vars).

## 5. Verification
- Rerun `meta_ray_test`. It might still fail if it needs scanner output.
- *Wait*, `meta_ray_test` sleeve `binance_spot_rating_ma_long` expects scanner results `scanners/crypto/ratings/binance_spot_rating_ma_long`.
- If we didn't run `scan-run` for this ID, `export/<RUN_ID>` is empty.
- **Correct Flow**:
    1. Host runs Scans (generating `export/<RUN_ID>`).
    2. Host dispatches Ray Workers.
    3. Ray Workers need access to `export/<RUN_ID>`.
    
- **Action**: `parallel_orchestrator_native.py` MUST symlink `export/` from host to worker (Read-Only).

