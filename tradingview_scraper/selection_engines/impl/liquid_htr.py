import logging
from typing import Dict

import pandas as pd

from tradingview_scraper.selection_engines.impl.v3_4_htr import SelectionEngineV3_4

logger = logging.getLogger("selection_engines")


class SelectionEngineLiquidHTR(SelectionEngineV3_4):
    """
    Structural Baseline Selection Engine.
    Uses full HTR v3.4 clustering and relaxation, but picks Top-N by
    Liquidity (Value.Traded) instead of Log-MPS statistical scoring.
    Used for isolating 'Statistical Alpha' from 'Clustering Alpha'.
    """

    @property
    def name(self) -> str:
        return "liquid_htr"

    def __init__(self):
        super().__init__()
        self.spec_version = "1.0-liquid-htr"

    def _calculate_alpha_scores(self, mps_metrics: Dict[str, pd.Series], methods: Dict[str, str], frag_penalty: pd.Series) -> pd.Series:
        """
        Overrides Log-MPS to return pure liquidity scores.
        """
        return mps_metrics["liquidity"]
