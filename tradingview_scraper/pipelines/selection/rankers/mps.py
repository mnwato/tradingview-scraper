from typing import List

from tradingview_scraper.pipelines.selection.base import SelectionContext
from tradingview_scraper.pipelines.selection.rankers.base import BaseRanker


class MPSRanker(BaseRanker):
    """
    Default Ranker: Sorts by Log-MPS 'alpha_score'.
    Compatible with v3.6 behavior.
    """

    def rank(self, candidates: List[str], context: SelectionContext, ascending: bool = False) -> List[str]:
        scores = context.inference_outputs["alpha_score"] if not context.inference_outputs.empty else {}

        def _get_score(s_id: str) -> float:
            val = scores.get(s_id)
            return float(val) if val is not None else -1.0

        # Note: ascending=True means Lowest Score First (e.g. for Short MA)
        # ascending=False means Highest Score First (Default Long)
        return sorted(candidates, key=_get_score, reverse=not ascending)
