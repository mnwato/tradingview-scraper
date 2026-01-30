import logging
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class SleeveAggregator:
    """
    Builds meta-returns matrix from individual sleeve performance.
    """

    def aggregate(self, sleeve_returns: Dict[str, pd.Series], join_method: str = "inner") -> pd.DataFrame:
        """
        Aggregate sleeve returns into a matrix.

        Args:
            sleeve_returns: Map of sleeve_name -> return_series.
            join_method: "inner" (common dates) or "outer" (all dates).

        Returns:
            DataFrame with sleeves as columns, dates as index.
        """
        if not sleeve_returns:
            return pd.DataFrame()

        # 1. Normalize Indices (UTC Naive)
        normalized = {}
        for name, series in sleeve_returns.items():
            if series.empty:
                logger.warning(f"Sleeve {name} returns are empty. Skipping.")
                continue

            s = series.copy()
            s.index = pd.to_datetime(s.index)
            if s.index.tz is not None:
                s.index = s.index.tz_convert(None)
            normalized[name] = s

        if not normalized:
            return pd.DataFrame()

        # 2. Join
        meta_df = pd.DataFrame(normalized)

        if join_method == "inner":
            meta_df = meta_df.dropna()

        return meta_df
