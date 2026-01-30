import logging
from typing import Any, Dict, List, Optional
from tradingview_scraper.pipelines.selection.rankers.base import BaseRanker
from tradingview_scraper.pipelines.selection.base import SelectionContext

logger = logging.getLogger(__name__)


class EnsembleRanker(BaseRanker):
    """
    Ranker that ensembles multiple sub-rankers using weighted averaging.
    """

    def __init__(self, rankers: Dict[str, BaseRanker], weights: Optional[Dict[str, float]] = None):
        self.rankers = rankers
        # Default to equal weights if not provided
        if weights is None:
            self.weights = {k: 1.0 / len(rankers) for k in rankers.keys()}
        else:
            self.weights = weights

        # Normalize weights to sum to 1.0
        total_w = sum(self.weights.values())
        if total_w > 0:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def rank(self, candidates: List[str], context: SelectionContext, ascending: bool = False) -> List[str]:
        """
        Sorts candidates by ensembled WoE score.
        """
        scores = self.score_map(candidates, context)
        # Sort symbols by score descending
        sorted_ids = sorted(candidates, key=lambda s: scores.get(s, 0.0), reverse=not ascending)
        return sorted_ids

    def score_map(self, candidates: List[str], context: SelectionContext) -> Dict[str, float]:
        """
        Internal: Aggregates scores from all sub-rankers into a map.
        """
        ensemble_scores: Dict[str, float] = {c: 0.0 for c in candidates}

        for name, ranker in self.rankers.items():
            weight = self.weights.get(name, 0.0)
            if weight == 0:
                continue

            try:
                # Use the new score() method from BaseRanker
                scores_list = ranker.score(candidates, context)
                for i, sym in enumerate(candidates):
                    ensemble_scores[sym] += scores_list[i] * weight
            except Exception as e:
                logger.error(f"Ranker {name} failed during ensemble: {e}")

        return ensemble_scores

    def score(self, candidates: List[str], context: SelectionContext) -> List[float]:
        """
        Returns the ensembled scores as a list.
        """
        s_map = self.score_map(candidates, context)
        return [s_map.get(c, 0.0) for c in candidates]
