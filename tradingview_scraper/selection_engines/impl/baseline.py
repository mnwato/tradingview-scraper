import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from tradingview_scraper.selection_engines.base import (
    BaseSelectionEngine,
    SelectionRequest,
    SelectionResponse,
    get_hierarchical_clusters,
)

logger = logging.getLogger("selection_engines")


class BaselineSelectionEngine(BaseSelectionEngine):
    """
    Baseline Selection Engine.
    Passes through ALL raw candidates to the portfolio engines without any filtering or vetoes.
    Used for quantifying the 'Alpha Value Added' by more advanced selection funnels.
    """

    @property
    def name(self) -> str:
        return "baseline"

    def select(
        self,
        returns: pd.DataFrame,
        raw_candidates: List[Dict[str, Any]],
        stats_df: Optional[pd.DataFrame],
        request: SelectionRequest,
    ) -> SelectionResponse:
        # 1. Map candidates to winners (pass everything)
        winners = []
        for cand in raw_candidates:
            winner = cand.copy()
            # If stats_df is available, try to attach alpha score if it exists
            # otherwise default to 0.0 or some neutral value
            if stats_df is not None and cand["symbol"] in stats_df.index:
                winner["alpha_score"] = float(stats_df.loc[cand["symbol"], "Antifragility_Score"])
            else:
                winner["alpha_score"] = 1.0  # Equal weight priority
            winners.append(winner)

        # 2. Provide clusters for the portfolio engines (still useful for HRP/Clustered)
        cluster_ids, _ = get_hierarchical_clusters(returns, request.threshold, request.max_clusters)
        clusters = {}
        winner_syms = {w["symbol"] for w in winners}
        for sym, c_id in zip(returns.columns, cluster_ids):
            cid = int(c_id)
            if cid not in clusters:
                clusters[cid] = {"size": 0, "selected": []}
            clusters[cid]["size"] += 1
            if str(sym) in winner_syms:
                clusters[cid]["selected"].append(str(sym))

        return SelectionResponse(
            winners=winners,
            audit_clusters=clusters,
            spec_version="1.0-baseline",
            metrics={"n_winners": len(winners), "n_vetoes": 0},
            warnings=["Baseline engine: No filtering applied."],
            vetoes={},
            relaxation_stage=1,
            active_thresholds={},
        )
