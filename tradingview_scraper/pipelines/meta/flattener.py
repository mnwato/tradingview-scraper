import logging
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class WeightFlattener:
    """
    Projects meta-weights (sleeve allocations) to individual asset weights.
    """

    def flatten(self, meta_weights: pd.Series, sleeve_weights: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Project meta-weights to atom-level weights.

        Formula: atom_weight = meta_weight[sleeve] * sleeve_weight[atom]

        Args:
            meta_weights: Series of sleeve allocations (sum = 1.0).
            sleeve_weights: Map of sleeve_name -> weight_df.
                Expected weight_df columns: [Symbol, Weight, Direction].

        Returns:
            DataFrame with columns [Symbol, Weight, Net_Weight, Direction, Sleeve].
        """
        all_atoms = []

        for sleeve_name, meta_w in meta_weights.items():
            if sleeve_name not in sleeve_weights:
                logger.warning(f"Sleeve {sleeve_name} weights missing. Skipping.")
                continue

            s_df = sleeve_weights[sleeve_name].copy()
            if s_df.empty:
                continue

            # Project weights
            # (Note: s_df["Weight"] is the weight WITHIN the sleeve)
            s_df["Weight"] = s_df["Weight"] * meta_w

            # Net Weight handles direction (SHORT = -Weight)
            if "Net_Weight" in s_df.columns:
                s_df["Net_Weight"] = s_df["Net_Weight"] * meta_w
            else:
                # Calculate from Weight and Direction if missing
                s_df["Net_Weight"] = s_df.apply(lambda x: -x["Weight"] if x.get("Direction") == "SHORT" else x["Weight"], axis=1)

            s_df["Sleeve"] = sleeve_name
            all_atoms.append(s_df)

        if not all_atoms:
            return pd.DataFrame()

        combined = pd.concat(all_atoms, ignore_index=True)

        # Aggregate duplicates (same asset in multiple sleeves)
        # e.g. BTC in "Long Trend" and "Short MA"
        final = combined.groupby(["Symbol", "Direction"]).agg({"Weight": "sum", "Net_Weight": "sum", "Sleeve": lambda x: ", ".join(x)}).reset_index()

        return final.sort_values("Weight", ascending=False)
