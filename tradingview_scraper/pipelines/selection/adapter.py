import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from tradingview_scraper.pipelines.selection.pipeline import SelectionPipeline
from tradingview_scraper.selection_engines.base import BaseSelectionEngine, SelectionRequest, SelectionResponse

logger = logging.getLogger("pipelines.selection.adapter")


class SelectionPipelineAdapter(BaseSelectionEngine):
    """
    Adapter to bridge the MLOps-centric v4 SelectionPipeline to the
    legacy BaseSelectionEngine interface expected by BacktestOrchestrator.
    """

    @property
    def name(self) -> str:
        return "v4_pipeline"

    def __init__(self):
        super().__init__()
        self.pipeline = SelectionPipeline(run_id="v4_adapter_run")

    def select(
        self,
        returns: pd.DataFrame,
        raw_candidates: List[Dict[str, Any]],
        stats_df: Optional[pd.DataFrame],
        request: SelectionRequest,
    ) -> SelectionResponse:
        """
        Executes the v4 pipeline and maps the result to SelectionResponse.
        """
        logger.info("Adapting v4 SelectionPipeline execution...")

        # 1. Update Pipeline State with Inputs
        # We manually inject data into the pipeline stages or context
        # Ideally, we pass paths to IngestionStage, but here we have in-memory data.
        # So we bypass IngestionStage file loading and set context directly.

        # Override Ingestion logic by pre-seeding the context
        # This requires a small refactor of Pipeline.run() to accept pre-loaded data?
        # Or we can just set it on the pipeline instance before run?
        # The pipeline.run() creates a NEW Context.

        # HACK: We subclass/modify Pipeline or we construct Context manually and pass it?
        # Pipeline.run() creates context.
        # Let's verify Pipeline.run signature.
        # def run(self, overrides: Optional[Dict[str, Any]] = None) -> SelectionContext:

        # We need a way to pass in-memory returns/candidates.
        # I'll add `inputs` arg to `run`.

        # For now, let's assume we update Pipeline to accept in-memory data.
        # I will implement `run_with_inputs`.

        # Wait, I can just modify the pipeline instance's stages? No, they are stateless.
        # I need to modify `SelectionPipeline.run`.

        # Let's implement the adapter assuming `run_with_data` exists, then I update Pipeline.

        # Map Request Params
        overrides = {"top_n": request.top_n, "cluster_threshold": request.threshold, "max_clusters": request.max_clusters, **request.params}
        # Only set relaxation_stage if explicitly provided in request.params
        # Otherwise let the pipeline loop internally

        # Execute
        # We need to inject returns and raw_candidates.
        context = self.pipeline.run_with_data(returns_df=returns, raw_candidates=raw_candidates, overrides=overrides)

        # Map Output to SelectionResponse
        # Reconstruct audit_clusters from context.clusters + winners
        # context.clusters is Dict[int, List[str]]
        # SelectionResponse.audit_clusters expects Dict[int, {'size': int, 'selected': List[str]}]

        winner_syms = {w["symbol"] for w in context.winners}
        audit_clusters = {}

        for cid, syms in context.clusters.items():
            selected = [s for s in syms if s in winner_syms]
            audit_clusters[int(cid)] = {"size": len(syms), "selected": selected}

        # Map Metrics
        # context.inference_outputs has scores
        # We need 'alpha_scores' dict
        alpha_scores = context.inference_outputs["alpha_score"].to_dict() if not context.inference_outputs.empty else {}

        metrics = {"alpha_scores": alpha_scores, "raw_metrics": context.feature_store.to_dict() if not context.feature_store.empty else {}, "pipeline_audit": context.audit_trail}

        return SelectionResponse(winners=context.winners, audit_clusters=audit_clusters, spec_version="4.0-mlops", metrics=metrics, relaxation_stage=int(context.params.get("relaxation_stage", 1)))
