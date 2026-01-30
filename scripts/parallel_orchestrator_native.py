import logging
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List

import ray

# Configure logging to capture Ray worker logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ray_native_orchestrator")


@ray.remote(num_cpus=1, memory=3 * 1024 * 1024 * 1024)
class SleeveProductionActor:
    """
    Stateful Ray Actor that executes a production pipeline in a dedicated process.
    Changes to CWD and Environment Variables are isolated to this actor's process.
    """

    def __init__(self, host_cwd: str, env_vars: Dict[str, str]):
        self.host_cwd = host_cwd

        # Import settings inside actor to ensure we get the right config
        # (env vars are updated below, but we need paths now)
        # We assume host_cwd is the root of the repo
        # However, for safety, let's use hardcoded "data" logic for symlinks
        # because the settings might not be fully loaded or might depend on env vars we just got.

        # ACTUALLY, let's use the env_vars passed in to initialize settings if needed?
        # Simpler: Just stick to the "data" folder structure which we just enforced.
        # But we want to use settings.data_dir etc.

        # Update env vars FIRST so get_settings sees them
        if "VIRTUAL_ENV" in env_vars:
            del env_vars["VIRTUAL_ENV"]

        # CR-FIX: Workspace Isolation Flags (Phase 234)
        env_vars["PORTFOLIO_DATA_SOURCE"] = "lakehouse_only"
        env_vars["TV_STRICT_HEALTH"] = "1"
        env_vars["TV_STRICT_ISOLATION"] = "1"

        os.environ.update(env_vars)

        try:
            import scripts.run_production_pipeline
            import tradingview_scraper
            from tradingview_scraper.settings import get_settings

            # Force reload settings to pick up new env vars
            get_settings.cache_clear()
            self.settings = get_settings()
        except ImportError as e:
            raise RuntimeError(f"Failed to import project modules in Ray Actor: {e}")

        # 1. Workspace Setup (Isolation)
        # We need to construct the 'data' directory structure locally to allow
        # mixed isolation:
        # - data/lakehouse: SYMLINK (Read-only shared input)
        # - data/export: SYMLINK (Shared scanner input)
        # - data/artifacts: LOCAL (Write-isolated output, exported at end)
        # - data/logs: LOCAL (Write-isolated logs)

        data_root = self.settings.data_dir
        if data_root.is_symlink():
            os.unlink(data_root)
        data_root.mkdir(parents=True, exist_ok=True)

        # Helper to symlink subdirectories
        def link_subdir(subdir_attr: str):
            target_path = getattr(self.settings, subdir_attr)  # e.g. data/lakehouse
            local_path = target_path  # path relative to CWD in actor
            host_path = Path(host_cwd) / target_path

            if local_path.exists():
                if local_path.is_symlink():
                    return  # Already linked
                if local_path.is_dir() and not any(local_path.iterdir()):
                    local_path.rmdir()  # Empty dir, safe to remove
                else:
                    logger.warning(f"⚠️ Local {local_path} exists and is not empty/link. Skipping link.")
                    return

            if host_path.exists():
                try:
                    os.symlink(host_path, local_path)
                    logger.info(f"🔗 Linked {local_path} -> {host_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to link {local_path}: {e}")
            else:
                logger.warning(f"⚠️ Host path {host_path} not found.")

        # Symlink Inputs
        link_subdir("lakehouse_dir")
        link_subdir("export_dir")

        # Create Outputs (Local)
        self.settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.settings.logs_dir.mkdir(parents=True, exist_ok=True)

        # CR-FIX: Symlink '.venv'
        if not os.path.exists(".venv"):
            try:
                host_venv = os.path.join(host_cwd, ".venv")
                if os.path.exists(host_venv):
                    os.symlink(host_venv, ".venv")
                    logger.info(f"🔗 Linked .venv from {host_venv}")
                else:
                    logger.warning(f"⚠️ Host .venv not found at {host_venv}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to symlink .venv: {e}")

    def run_pipeline(self, profile: str, run_id: str) -> Dict:
        start_time = time.time()
        logger.info(f"🚀 [Ray Native] Starting pipeline for {profile} (Run: {run_id})")

        # DEBUG PROBE: Check environment before execution
        try:
            import tradingview_scraper

            logger.info(f"🔍 Actor Import: {tradingview_scraper.__file__}")

            import subprocess

            # Check what 'uv run' sees
            probe = subprocess.run(
                ["uv", "run", "python", "-c", "import tradingview_scraper; print('UV Import:', tradingview_scraper.__file__)"], capture_output=True, text=True, cwd=os.getcwd(), env=os.environ
            )
            logger.info(f"🔍 UV Probe STDOUT: {probe.stdout.strip()}")
            logger.info(f"🔍 UV Probe STDERR: {probe.stderr.strip()}")
        except Exception as e:
            logger.warning(f"⚠️ Probe failed: {e}")

        status = "success"
        error_msg = None

        try:
            # Dynamic import to avoid top-level side effects during worker init
            from scripts.run_production_pipeline import ProductionPipeline

            # Instantiate and Execute
            # The pipeline class handles settings reload via cache_clear()
            pipeline = ProductionPipeline(profile=profile, run_id=run_id)
            pipeline.execute()

        except Exception as e:
            logger.error(f"❌ [Ray Native] Pipeline failed for {profile}: {e}", exc_info=True)
            status = "error"
            error_msg = str(e)

        finally:
            # ---------------------------------------------------------
            # ARTIFACT EXPORT PATTERN (Phase 234)
            # ---------------------------------------------------------
            # We must export artifacts even if the pipeline failed (to capture logs).

            # Use settings for paths
            # Note: pipeline.settings might be updated, but self.settings is what we init with.
            # Let's re-get settings just in case
            from tradingview_scraper.settings import get_settings

            settings = get_settings()

            run_artifacts_path = settings.summaries_runs_dir / run_id

            if run_artifacts_path.exists():
                logger.info(f"📦 Zipping artifacts from {run_artifacts_path}")

                try:
                    # Create ZIP in current worker dir
                    archive_name = f"artifacts_{run_id}"
                    # Base dir for zip should probably be relative to artifacts root?
                    # shutil.make_archive(base_name, format, root_dir, base_dir)
                    # root_dir is the directory that will be the root of the archive
                    # base_dir is the directory where we start archiving from inside root_dir

                    # We want the zip to contain "summaries/runs/<run_id>/..."
                    # So root_dir = settings.artifacts_dir (e.g. data/artifacts)
                    # base_dir = summaries/runs/<run_id>

                    # Construct relative path for base_dir
                    rel_base = run_artifacts_path.relative_to(settings.artifacts_dir)

                    shutil.make_archive(archive_name, "zip", root_dir=str(settings.artifacts_dir), base_dir=str(rel_base))

                    # Export to Host
                    # Host path construction:
                    dest_dir = Path(self.host_cwd) / settings.summaries_runs_dir / run_id

                    # Ensure parent exists
                    dest_dir.parent.mkdir(parents=True, exist_ok=True)

                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)  # Overwrite if exists (re-run)

                    shutil.copytree(run_artifacts_path, dest_dir)
                    logger.info(f"✅ Exported artifacts to {dest_dir}")
                except Exception as export_err:
                    logger.error(f"❌ Failed to export artifacts: {export_err}")
            else:
                logger.warning(f"⚠️ No artifacts found at {run_artifacts_path} to export")

        duration = time.time() - start_time
        result = {"profile": profile, "run_id": run_id, "status": status, "duration": duration, "node": ray.util.get_node_ip_address()}
        if error_msg:
            result["error"] = error_msg

        return result


def execute_parallel_sleeves_native(sleeves: List[Dict]) -> List[Dict]:
    """
    Orchestrates multiple sleeve runs using Ray Native Actors.
    """
    # 1. Capture Host State
    host_cwd = os.getcwd()

    # Capture relevant env vars to propagate
    env_vars = {k: v for k, v in os.environ.items() if k.startswith("TV_") or k in ["PYTHONPATH", "PATH", "UV_PROJECT_ENVIRONMENT"]}

    # 2. Initialize Ray with Runtime Env (Isolation)
    if not ray.is_initialized():
        # Exclude heavy directories to prevent upload/copy overhead
        # We rely on Symlinking 'data' in the actor.
        runtime_env = {"working_dir": ".", "excludes": ["data", ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".opencode"]}
        ray.init(runtime_env=runtime_env, ignore_reinit_error=True)

    logger.info(f"Initialized Ray Native Orchestration. Dispatching {len(sleeves)} sleeves.")

    # 3. Spawn Actors (One per sleeve to ensure total isolation)
    # We could reuse actors, but for production safety, fresh actors are preferred.
    actors = [SleeveProductionActor.remote(host_cwd, env_vars) for _ in sleeves]

    # 4. Dispatch Tasks
    futures = [actor.run_pipeline.remote(s["profile"], s["run_id"]) for actor, s in zip(actors, sleeves)]

    # 5. Await Results
    results = ray.get(futures)

    # 6. Cleanup (Optional, Ray handles this on script exit usually)
    for actor in actors:
        ray.kill(actor)

    return results
