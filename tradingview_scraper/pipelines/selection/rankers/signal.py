import logging
from typing import List

from tradingview_scraper.pipelines.selection.base import SelectionContext
from tradingview_scraper.pipelines.selection.rankers.base import BaseRanker

logger = logging.getLogger("pipelines.selection.rankers.signal")


class SignalRanker(BaseRanker):
    """
    Ranks candidates based on a raw feature column (e.g., 'recommend_ma', 'rsi').
    Useful for single-factor strategies that want to bypass the MPS ensemble.
    """

    def __init__(self, signal_name: str):
        self.signal_name = signal_name

    def rank(self, candidates: List[str], context: SelectionContext, ascending: bool = False) -> List[str]:
        features = context.feature_store

        if self.signal_name not in features.columns:
            logger.warning(f"SignalRanker: Feature '{self.signal_name}' not found. Fallback to unsorted.")
            return candidates

        def _get_signal(s_id: str) -> float:
            try:
                val = features.loc[s_id, self.signal_name]
                return float(val) if val is not None else 0.0
            except (KeyError, ValueError, TypeError):
                return 0.0

        return sorted(candidates, key=_get_signal, reverse=not ascending)
