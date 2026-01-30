import logging
from typing import Dict, List

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.pipelines.selection.base import BasePipelineStage, SelectionContext
from tradingview_scraper.utils.clustering import get_hierarchical_clusters

logger = logging.getLogger("pipelines.selection.clustering")


@StageRegistry.register(id="alpha.clustering", name="Clustering", description="Orthogonal factor partitioning", category="alpha")
class ClusteringStage(BasePipelineStage):
    """
    Stage 4: Manifold Partitioning (Clustering).
    Groups assets into orthogonal factor buckets using Ward Linkage on the correlation matrix.
    """

    @property
    def name(self) -> str:
        return "Clustering"

    def execute(self, context: SelectionContext) -> SelectionContext:
        returns = context.returns_df
        if returns.empty or len(returns.columns) < 2:
            logger.warning("ClusteringStage: Not enough assets to cluster. Assigning all to Cluster 1.")
            context.clusters = {1: list(returns.columns)}
            return context

        # Parameters (default to v3.4 standard)
        threshold = context.params.get("cluster_threshold", 0.7)
        max_clusters = context.params.get("max_clusters", 10)

        logger.info(f"Executing Hierarchical Clustering (Thresh={threshold}, Max={max_clusters})...")

        # Reuse existing robust clustering logic
        cluster_ids, _ = get_hierarchical_clusters(returns, threshold, max_clusters)

        # Transform flat array to Dict[ClusterID, List[Symbol]]
        clusters: Dict[int, List[str]] = {}
        for sym, c_id in zip(returns.columns, cluster_ids):
            cid = int(c_id)
            if cid not in clusters:
                clusters[cid] = []
            clusters[cid].append(str(sym))

        context.clusters = clusters
        context.log_event(self.name, "PartitioningComplete", {"n_clusters": len(clusters), "sizes": {k: len(v) for k, v in clusters.items()}})

        return context
