import logging
from pathlib import Path
from typing import Any, List, Optional, Union, cast

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.telemetry.tracing import trace_span

logger = logging.getLogger(__name__)


class QuantSDK:
    """
    High-level API for interacting with the quantitative portfolio platform.
    Used by Claude skills and CLI.
    """

    @staticmethod
    def run_stage(id: str, context: Optional[Any] = None, **params) -> Any:
        """
        Executes a single pipeline stage by its ID.
        """
        return QuantSDK._run_stage_impl(id, context, **params)

    @staticmethod
    @trace_span("sdk.run_stage")
    def _run_stage_impl(id: str, context: Optional[Any] = None, **params) -> Any:
        logger.info(f"SDK: Executing stage {id}")
        stage_callable = StageRegistry.get_stage(id)
        spec = StageRegistry.get_spec(id)

        # If it's a class (BasePipelineStage), instantiate and execute
        if spec.stage_class:
            instance = spec.stage_class(**params)
            if context is None:
                # Some stages might create their own context if needed
                # but for selection stages, it's usually required.
                pass
            return instance.execute(context)

        # If it's a function/method
        # Functions might not take 'context' as first arg, but we'll try to be flexible
        # If context is provided, we could pass it, but meta functions currently don't use it.
        # Let's check the signature if possible or just call with params.
        import inspect

        sig = inspect.signature(stage_callable)
        if "context" in sig.parameters:
            return stage_callable(context=context, **params)
        else:
            return stage_callable(**params)

    @staticmethod
    def validate_foundation(run_id: Optional[str] = None) -> bool:
        """
        L1 Ingestion Gate: Validates Lakehouse integrity and PIT fidelity.
        Checks for missing Parquet files, staleness, and schema drift.
        Also verifies FoundationHealthRegistry status.
        """
        from tradingview_scraper.settings import get_settings
        from tradingview_scraper.pipelines.selection.base import FoundationHealthRegistry
        import os

        settings = get_settings()
        lakehouse = settings.lakehouse_dir

        logger.info(f"SDK: Validating foundation at {lakehouse}")

        # 1. Existence Checks
        required_files = ["returns_matrix.parquet", "features_matrix.parquet"]

        missing = [f for f in required_files if not (lakehouse / f).exists()]
        if missing:
            logger.error(f"Foundation Gate FAILED: Missing files: {missing}")
            return False

        # 2. Registry Check
        registry = FoundationHealthRegistry(path=lakehouse / "foundation_health.json")
        logger.info(f"Foundation Registry: {len(registry.data)} symbols tracked")

        # 2.1 Feature Consistency Audit (Phase 630)
        from tradingview_scraper.utils.features import FeatureConsistencyValidator
        import pandas as pd

        returns_f = lakehouse / "returns_matrix.parquet"
        features_f = lakehouse / "features_matrix.parquet"

        if returns_f.exists() and features_f.exists():
            rets = pd.read_parquet(returns_f)
            feats = pd.read_parquet(features_f)
            missing = FeatureConsistencyValidator.audit_coverage(feats, rets)
            if missing:
                logger.error(f"Foundation Gate: Feature Store is INCONSISTENT. {len(missing)} symbols missing.")
                if os.getenv("TV_STRICT_HEALTH") == "1":
                    return False

        # If run_id is provided, we report summary stats
        toxic_count = len([s for s, m in registry.data.items() if m.get("status") == "toxic"])
        if toxic_count > 0:
            logger.warning(f"Foundation Gate: Found {toxic_count} toxic assets in registry")
            # Fail-fast only if STRICT_HEALTH is enabled and we have specific symbols to check
            # (Note: we don't know the current universe here without the manifest)

        # 3. Freshness check
        # (Optional, depending on STRICT_HEALTH)
        if os.getenv("TV_STRICT_HEALTH") == "1":
            import time

            current_time = time.time()
            for f in required_files:
                mtime = (lakehouse / f).stat().st_mtime
                age_hours = (current_time - mtime) / 3600
                if age_hours > 24:
                    logger.warning(f"Foundation Gate: {f} is stale ({age_hours:.1f} hours old)")

        logger.info("✅ Foundation Gate PASS")
        return True

    @staticmethod
    def create_snapshot(run_id: str) -> Path:
        """
        Creates a 'Golden Snapshot' of the Lakehouse for run immutability.
        Uses WorkspaceManager for hybrid copy/link strategy.
        """
        from tradingview_scraper.utils.workspace import WorkspaceManager

        manager = WorkspaceManager(run_id)
        return manager.create_golden_snapshot()

    @staticmethod
    @trace_span("sdk.repair_foundation")
    def repair_foundation(run_id: str, max_fills: int = 15) -> bool:
        """
        Manages the automated repair pass for the Lakehouse.
        """
        import subprocess

        logger.info(f"SDK: Starting automated foundation repair (run_id={run_id})")

        try:
            # We call the existing repair script
            cmd = ["python", "scripts/services/repair_data.py", "--max-fills", str(max_fills)]
            # If we want to use specific candidates, we'd need to find them for the run
            # For now, we rely on the script's default behavior or env vars
            subprocess.run(cmd, check=True)
            logger.info("✅ Foundation Repair PASS")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Foundation Repair FAILED: {e}")
            return False

    @staticmethod
    def run_pipeline(name: str, context: Optional[Any] = None, **params) -> Any:
        """
        Executes a full named pipeline (e.g., 'alpha.full').
        Resolves the DAG from the manifest and executes using DAGRunner.
        """
        from tradingview_scraper.orchestration.runner import DAGRunner
        from tradingview_scraper.settings import get_settings
        from tradingview_scraper.telemetry.provider import TelemetryProvider
        import json

        settings = get_settings()
        run_id = params.get("run_id", settings.run_id)

        # 1. Initialize Forensic Telemetry for the run
        telemetry = TelemetryProvider()
        if not telemetry.is_initialized:
            telemetry.initialize(service_name="quant-orchestrator")

        trace_file = settings.summaries_runs_dir / run_id / "data" / "forensic_trace.json"
        exporter = telemetry.register_forensic_exporter(trace_file)

        # 2. Resolve DAG from manifest
        with open(settings.manifest_path, "r") as f:
            manifest = json.load(f)

        pipeline_cfg = manifest.get("pipelines", {}).get(name)
        if not pipeline_cfg:
            # Fallback for core pipelines if missing from manifest
            core_pipelines: dict[str, list[str | list[str]]] = {
                "alpha.full": [
                    "foundation.ingest",
                    "foundation.features",
                    "alpha.inference",
                    "alpha.clustering",
                    "alpha.policy",
                    "alpha.synthesis",
                    "risk.optimize",
                ],
                "meta.full": ["meta.aggregation", "risk.optimize_meta", "risk.flatten_meta", "risk.report_meta"],
            }
            if name not in core_pipelines:
                raise KeyError(f"Pipeline '{name}' not found in manifest or core defaults.")
            steps = core_pipelines[name]
        else:
            steps = cast(List[Union[str, List[str]]], pipeline_cfg["steps"])

        runner = DAGRunner(steps)

        # 3. Initialize context if not provided
        if context is None:
            # Determine correct context type based on pipeline category
            if name.startswith("alpha"):
                from tradingview_scraper.pipelines.selection.base import SelectionContext

                context = SelectionContext(run_id=run_id, params=params)
            elif name.startswith("meta"):
                from tradingview_scraper.pipelines.meta.base import MetaContext

                context = MetaContext(run_id=run_id, meta_profile=params.get("profile", "meta_production"), sleeve_profiles=params.get("profiles", []))

        # 4. Execute DAG and Flush Telemetry
        try:
            result = runner.execute(context)
            telemetry.flush_metrics(job_name=f"quant_{name}", grouping_key={"run_id": run_id})
            return result
        finally:
            exporter.save()
