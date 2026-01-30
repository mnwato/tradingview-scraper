import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import ray

from tradingview_scraper.settings import get_settings
from tradingview_scraper.telemetry.context import extract_trace_context
from tradingview_scraper.telemetry.provider import TelemetryProvider
from tradingview_scraper.telemetry.tracing import trace_span

logger = logging.getLogger(__name__)


class SleeveActorImpl:
    """
    Stateful Ray Actor Implementation that executes a strategy sleeve's production pipeline.
    Handles process isolation, environment propagation, and artifact export.
    """

    def __init__(self, host_cwd: str, env_vars: Dict[str, str], trace_context: Optional[Dict[str, str]] = None):
        self.host_cwd = host_cwd

        # 1. Environment Setup
        if "VIRTUAL_ENV" in env_vars:
            del env_vars["VIRTUAL_ENV"]

        # Enforce Production Isolation Defaults
        env_vars["TV_STRICT_HEALTH"] = "1"
        env_vars["TV_STRICT_ISOLATION"] = "1"

        os.environ.update(env_vars)

        # 2. Telemetry Initialization (Distributed Trace Linkage)
        self.provider = TelemetryProvider()
        self.provider.initialize(service_name="sleeve-actor")
        self.trace_context = trace_context

        # 3. Settings Initialization
        get_settings.cache_clear()
        self.settings = get_settings()

        # 4. Workspace Isolation (WorkspaceManager)
        from tradingview_scraper.utils.workspace import WorkspaceManager

        self.workspace = WorkspaceManager(run_id=os.getenv("TV_RUN_ID", "remote_run"))
        self.workspace.setup_worker_workspace(worker_cwd=Path(os.getcwd()), host_cwd=Path(host_cwd))

    def _setup_workspace(self):
        """Deprecated: Logic moved to WorkspaceManager."""
        pass

    @trace_span("sleeve_actor.run_pipeline")
    def run_pipeline(self, profile: str, run_id: str) -> Dict[str, Any]:
        """
        Executes the ProductionPipeline for the given profile.
        Exports resulting artifacts back to the host filesystem.
        """
        start_time = time.time()
        logger.info(f"🚀 [Ray] Starting sleeve production: {profile} (Run: {run_id})")

        status = "success"
        error_msg = None

        # Extract parent trace context if available
        context = extract_trace_context(self.trace_context) if self.trace_context else None

        from tradingview_scraper.telemetry.tracing import get_tracer

        tracer = get_tracer()
        with tracer.start_as_current_span("run_production_pipeline", context=context):
            try:
                from scripts.run_production_pipeline import ProductionPipeline

                # The pipeline class handles its own run_id directory preparation
                pipeline = ProductionPipeline(profile=profile, run_id=run_id)
                pipeline.execute()

            except Exception as e:
                logger.error(f"❌ [Ray] Pipeline failed for {profile}: {e}", exc_info=True)
                status = "error"
                error_msg = str(e)
            finally:
                self._export_artifacts(run_id)

        duration = time.time() - start_time
        return {"profile": profile, "run_id": run_id, "status": status, "duration": duration, "error": error_msg, "node": ray.util.get_node_ip_address()}

    def get_telemetry_spans(self) -> List[Dict[str, Any]]:
        """Returns the captured telemetry spans from this worker."""
        # Find the forensic exporter in the tracer provider
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from tradingview_scraper.telemetry.exporter import ForensicSpanExporter

        tp = trace.get_tracer_provider()
        # opentelemetry-sdk internal access
        if isinstance(tp, TracerProvider):
            # Accessing private attribute for forensic collection
            processors = getattr(tp, "_active_span_processor", None)
            if processors:
                for proc in processors._span_processors:
                    if isinstance(proc, SimpleSpanProcessor) and isinstance(proc.span_exporter, ForensicSpanExporter):
                        return proc.span_exporter.spans
        return []

    def _export_artifacts(self, run_id: str):
        """Copies local artifacts back to the host filesystem."""
        local_run_dir = self.settings.summaries_runs_dir / run_id
        host_run_dir = Path(self.host_cwd) / self.settings.summaries_runs_dir / run_id

        if local_run_dir.exists():
            logger.info(f"📦 Exporting artifacts for {run_id}")
            host_run_dir.parent.mkdir(parents=True, exist_ok=True)

            if host_run_dir.exists():
                shutil.rmtree(host_run_dir)

            shutil.copytree(local_run_dir, host_run_dir)
            logger.info(f"✅ Artifacts exported to host: {host_run_dir}")
        else:
            logger.warning(f"⚠️ No artifacts found at {local_run_dir} to export.")


# Define the Ray Actor with aggressive memory capping for constrained local environments
SleeveActor = ray.remote(num_cpus=1, memory=0.5 * 1024 * 1024 * 1024)(SleeveActorImpl)
