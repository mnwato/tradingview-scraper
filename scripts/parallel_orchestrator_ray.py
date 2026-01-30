import logging
import os
import subprocess
import time
from typing import Dict, List

import ray

logger = logging.getLogger("ray_orchestrator")


@ray.remote(num_cpus=2, memory=3 * 1024 * 1024 * 1024)
def run_sleeve_production(profile: str, run_id: str, host_cwd: str) -> Dict:
    """
    Executes a single sleeve's production pipeline as a Ray task.
    """
    start_time = time.time()
    logger.info(f"🚀 [Ray] Starting production for {profile} (Run: {run_id})")

    # CR-FIX: Use host_cwd to ensure artifacts are written to the host filesystem
    # and we use the host's environment/dependencies correctly.
    cwd = host_cwd

    # Use uv from the host environment if available, otherwise sys.executable
    cmd = ["uv", "run", "python", "-m", "scripts.run_production_pipeline", "--profile", profile, "--run-id", run_id]

    # Explicitly inherit and propagate important environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = cwd + ":" + env.get("PYTHONPATH", "")
    env["TV_PROFILE"] = profile
    env["TV_RUN_ID"] = run_id

    # CR-FIX: Unset VIRTUAL_ENV so 'uv' in the subprocess finds the host's .venv
    # instead of the ephemeral Ray worker venv.
    if "VIRTUAL_ENV" in env:
        del env["VIRTUAL_ENV"]

    # Force use of local python and uv for Ray tasks
    # CR-FIX: Ensure 'uv' is in PATH for make commands
    import shutil

    uv_path = shutil.which("uv")
    path_dirs = []
    if uv_path:
        path_dirs.append(os.path.dirname(uv_path))

    # Prepend to existing PATH
    env["PATH"] = ":".join(path_dirs) + ":" + env.get("PATH", "")

    try:
        # Capture output to prevent interleaving
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd, env=env)
        duration = time.time() - start_time
        return {"profile": profile, "run_id": run_id, "status": "success", "duration": duration, "stdout_tail": result.stdout[-500:]}
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ [Ray] Task failed for {profile}: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return {"profile": profile, "run_id": run_id, "status": "error", "error": str(e), "stderr": e.stderr}


def execute_parallel_sleeves(sleeves: List[Dict]) -> List[Dict]:
    """
    Orchestrates multiple sleeve runs using Ray.
    """
    if not ray.is_initialized():
        # CR-FIX: Standard init. Subprocesses will use the local env
        # since we are running on a single node.
        ray.init(ignore_reinit_error=True)

    host_cwd = os.getcwd()
    futures = [run_sleeve_production.remote(s["profile"], s["run_id"], host_cwd) for s in sleeves]

    results = ray.get(futures)
    return results
