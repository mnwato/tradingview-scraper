from abc import ABC, abstractmethod
from typing import List

from tradingview_scraper.pipelines.selection.base import SelectionContext


class BaseRanker(ABC):
    """
    Abstract interface for candidate ranking logic.
    Decouples sorting/scoring from the Policy Stage.
    """

    @abstractmethod
    def rank(self, candidates: List[str], context: SelectionContext, ascending: bool = False) -> List[str]:
        """
        Sorts the candidate list based on the ranker's logic.
        """
        pass

    def score(self, candidates: List[str], context: SelectionContext) -> List[float]:
        """
        Optional: returns raw scores for candidates.
        If not implemented, returns ranks as scores.
        """
        # Default implementation: use rank to return normalized scores [0, 1]
        sorted_ids = self.rank(candidates, context, ascending=True)
        id_to_rank = {id_: i / (len(sorted_ids) - 1) if len(sorted_ids) > 1 else 1.0 for i, id_ in enumerate(sorted_ids)}
        return [id_to_rank.get(c, 0.0) for c in candidates]
