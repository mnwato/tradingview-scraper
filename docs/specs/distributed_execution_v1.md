# Specification: Distributed Execution & Artifact Persistence (v1)

## 1. Overview
As the platform scales to cloud-native execution (Ray Clusters), the execution engine must transition from a **Shared Filesystem** model (Local Execution) to an **Isolated Filesystem** model (Distributed Execution).

## 2. Requirements

### 2.1 Isolation
- **REQ-ISO-001**: Worker processes MUST NOT assume access to the Driver's (Orchestrator's) filesystem.
- **REQ-ISO-002**: Worker processes MUST execute within a self-contained environment defined by `runtime_env`.
- **REQ-ISO-003**: The execution environment MUST include the full codebase and configuration, excluding heavy data artifacts (to minimize transmission overhead).

### 2.2 Persistence
- **REQ-PER-001 (Artifact Export)**: All artifacts generated during a pipeline step (logs, data, reports) MUST be explicitly exported to a persistent store upon completion.
- **REQ-PER-002 (Atomic Bundling)**: Artifacts for a specific `RUN_ID` should be bundled (e.g., ZIP archive) to ensure atomic transfer and consistency.
- **REQ-PER-003 (Failure Safety)**: If a task fails, available logs MUST still be exported to aid debugging.

### 2.3 Compatibility
- **REQ-COMP-001**: The system MUST support "Local Mode" (current behavior) where "Export" is simply a move/copy to the local `artifacts/` directory.

## 3. Technical Design (Ray Native)

### 3.1 Orchestrator Changes
- **Input**: The Orchestrator constructs a `runtime_env` with `working_dir="."` and `excludes=["artifacts/", "data/lakehouse/"]`.
- **Output Handling**: The Orchestrator waits for the worker to return a `persistence_manifest` (list of saved files) or receives the binary data directly (if small) or a path to the blob (if using shared storage).
- **For Phase 234**: We implement the **Local Loopback**:
    1. Worker runs in temp dir.
    2. Worker writes to `./artifacts/...`.
    3. Worker ZIPs `./artifacts` -> `results.zip`.
    4. Worker reads `results.zip` (if <100MB) and returns bytes OR copies to a mounted shared path if available.
    *Refinement*: Since we are running on a single machine (mostly), we can just `shutil.copy` from the worker's temp dir to the known host path passed as an argument, *provided the worker has write access to the host path*. 
    *Wait*, if we want strict isolation, we shouldn't assume write access to arbitrary host paths.
    *Better approach for TDD*: Return the artifacts as a return value (if small) or use a "Transfer Object" pattern.
    
    *Revised Plan for Phase 234*: 
    The Worker will `shutil.make_archive` the run directory.
    The Worker will returns the *content* of the archive or the path to a shared location.
    
    *Actually*, for the "Native" migration step on a single machine, we can cheat slightly: Pass `host_output_dir` to the worker. The worker does its work in isolation, then as a final step, copies the result to `host_output_dir`. This verifies the work *was* done in isolation, but allows simple persistence.

## 4. Test Plan (TDD)
We will create `tests/test_distributed_isolation.py`.

### Test Case 1: `test_execution_isolation`
- **Setup**: Create a dummy script that writes to `os.getcwd()/output.txt`.
- **Action**: Run this script via Ray with `working_dir`.
- **Assertion**:
    1. `output.txt` does NOT exist in the Driver's CWD.
    2. The task returns success.
    3. The task returns the *content* of `output.txt` (proving it existed in the worker).

### Test Case 2: `test_artifact_persistence`
- **Setup**: Configure `ParallelOrchestrator` to run a dummy pipeline.
- **Action**: Execute.
- **Assertion**: Artifacts appear in `artifacts/summaries/runs/<run_id>` on the host, even though the worker ran in `/tmp/...`.
