import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class FeatureConsistencyValidator:
    """
    Validates the Point-in-Time (PIT) integrity of the feature store.
    """

    @staticmethod
    def audit_coverage(features_df: pd.DataFrame, returns_df: pd.DataFrame) -> List[str]:
        """
        Ensures that all symbols in returns have corresponding features.
        Returns a list of missing symbols.
        """
        if features_df.empty or returns_df.empty:
            return []

        # Handle MultiIndex columns in features (symbol, feature)
        if isinstance(features_df.columns, pd.MultiIndex):
            feature_symbols = set(features_df.columns.get_level_values(0).unique())
        else:
            feature_symbols = set(features_df.columns)

        return_symbols = set(returns_df.columns)

        missing = sorted(list(return_symbols - feature_symbols))
        if missing:
            logger.warning(f"Feature Store Audit: {len(missing)} symbols missing from feature matrix: {missing[:5]}...")

        return missing

    @staticmethod
    def check_nan_density(series: pd.Series, max_pct: float = 0.10) -> bool:
        """
        Returns True if the series is 'Degraded' (NaN density > max_pct).
        Ignores leading NaNs (warm-up).
        """
        first_valid = series.first_valid_index()
        if first_valid is None:
            return True

        production_history = series.loc[first_valid:]
        nan_pct = production_history.isna().mean()

        return bool(nan_pct > max_pct)
