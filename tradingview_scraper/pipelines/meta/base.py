from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from tradingview_scraper.pipelines.selection.base import SelectionContext


class MetaContext(BaseModel):
    """
    Extended context for Meta-Portfolio construction.
    Aggregates results from multiple atomic sleeves.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str
    meta_profile: str
    params: Dict[str, Any] = Field(default_factory=dict)

    # Sleeve-Level Data
    sleeve_profiles: List[str] = Field(default_factory=list)
    sleeve_weights: Dict[str, pd.DataFrame] = Field(default_factory=dict)  # profile -> weight_df
    sleeve_returns: Dict[str, pd.Series] = Field(default_factory=dict)  # profile -> cumulative_return_series

    # Meta-Level Data
    meta_returns: pd.DataFrame = Field(default_factory=pd.DataFrame)  # Sleeves as columns
    meta_weights: pd.Series = Field(default_factory=lambda: pd.Series())  # Sleeve allocations

    # Final Output
    flattened_weights: pd.DataFrame = Field(default_factory=pd.DataFrame)  # Asset-level weights

    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)

    def log_event(self, stage: str, event: str, data: Optional[Dict[str, Any]] = None):
        self.audit_trail.append({"stage": stage, "event": event, "data": data or {}})
