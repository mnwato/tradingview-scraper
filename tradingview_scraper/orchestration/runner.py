import logging
from typing import Any, List, Union

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.telemetry.tracing import trace_span

logger = logging.getLogger(__name__)


class DAGRunner:
    """
    Orchestrates the execution of a Directed Acyclic Graph (DAG) of pipeline stages.
    Supports sequential and parallel branch execution.
    """

    def __init__(self, steps: List[Union[str, List[str]]]):
        """
        Args:
            steps: A list of stage IDs or sub-lists of stage IDs (for parallel execution).
        """
        self.steps = steps

    @trace_span("dag.execute")
    def execute(self, context: Any) -> Any:
        """
        Executes the DAG using the provided context.
        Returns the final transformed context.
        """
        logger.info(f"DAGRunner: Starting execution with {len(self.steps)} steps")

        current_context = context

        for step in self.steps:
            if isinstance(step, str):
                # Sequential Stage
                current_context = self._run_stage(step, current_context)
            elif isinstance(step, list):
                # Parallel Branches
                current_context = self._run_parallel(step, current_context)
            else:
                raise TypeError(f"Invalid step type: {type(step)}")

        logger.info("DAGRunner: Execution complete")
        return current_context

    def _run_stage(self, stage_id: str, context: Any) -> Any:
        """Executes a single stage via the SDK logic."""
        from tradingview_scraper.orchestration.sdk import QuantSDK

        # We use the internal implementation to avoid nested dag.execute spans
        # if run_stage itself is decorated (which it is via QuantSDK).
        # Actually, QuantSDK._run_stage_impl is what we want.
        return QuantSDK.run_stage(stage_id, context=context)

    def _run_parallel(self, branch_ids: List[str], context: Any) -> Any:
        """Executes multiple stages in parallel using Ray if available."""
        import os
        import copy

        use_parallel = os.getenv("TV_ORCH_PARALLEL") == "1"

        if not use_parallel:
            logger.info(f"DAGRunner: Executing {len(branch_ids)} branches sequentially (TV_ORCH_PARALLEL != 1)")
            for stage_id in branch_ids:
                # We work on copies to simulate parallel isolation
                branch_ctx = copy.deepcopy(context)
                branch_res = self._run_stage(stage_id, branch_ctx)
                context = self._merge_contexts(context, branch_res)
            return context

        # Ray execution for parallel branches
        from tradingview_scraper.orchestration.compute import RayComputeEngine
        import ray

        logger.info(f"DAGRunner: Dispatching {len(branch_ids)} branches to Ray")

        @ray.remote
        def execute_remote(sid: str, ctx: Any):
            from tradingview_scraper.orchestration.sdk import QuantSDK

            return QuantSDK.run_stage(sid, context=ctx)

        with RayComputeEngine() as engine:
            engine.ensure_initialized()
            futures = [execute_remote.remote(sid, copy.deepcopy(context)) for sid in branch_ids]
            results = ray.get(futures)

            for res in results:
                context = self._merge_contexts(context, res)

        return context

    def _merge_contexts(self, base: Any, overlay: Any) -> Any:
        """Merges two context objects using additive and concatenation protocols."""
        if base is None:
            return overlay

        # 1. SelectionContext Merging
        from tradingview_scraper.pipelines.selection.base import SelectionContext

        if isinstance(base, SelectionContext) and isinstance(overlay, SelectionContext):
            import pandas as pd

            # Merge Feature Store (Concatenate distinct columns)
            if not overlay.feature_store.empty:
                if base.feature_store.empty:
                    base.feature_store = overlay.feature_store
                else:
                    # Only add new columns
                    new_cols = overlay.feature_store.columns.difference(base.feature_store.columns)
                    if not new_cols.empty:
                        base.feature_store = pd.concat([base.feature_store, overlay.feature_store[new_cols]], axis=1)

            # Merge Audit Trail (Append only new entries)
            # Assumption: audit_trail is strictly additive.
            if len(overlay.audit_trail) > len(base.audit_trail):
                # This is a bit risky if base was modified since the branch started
                # but for now we assume branches are isolated.
                new_entries = overlay.audit_trail[len(base.audit_trail) :]
                base.audit_trail.extend(new_entries)

            return base

        # 2. Dict-based context (for generic/test steps)
        if isinstance(base, dict) and isinstance(overlay, dict):
            for k, v in overlay.items():
                if k in base and isinstance(base[k], list) and isinstance(v, list):
                    # List suffix merge (like audit trails)
                    if len(v) > len(base[k]):
                        new_items = v[len(base[k]) :]
                        base[k].extend(new_items)
                else:
                    base[k] = v
            return base

        # Fallback: override base with overlay
        return overlay
