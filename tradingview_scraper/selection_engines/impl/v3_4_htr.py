import dataclasses
import logging

from tradingview_scraper.selection_engines.impl.v3_mps import SelectionEngineV3_2

logger = logging.getLogger("selection_engines")


class SelectionEngineV3_4(SelectionEngineV3_2):
    """
    v3.4: Stabilized HTR Standard.
    - Integrates the 4-stage Hierarchical Threshold Relaxation loop.
    - Stage 1: Strict Vetoes (Institutional Defaults).
    - Stage 2: 20% Spectral Relaxation.
    - Stage 3: Factor Representation Floor (Force 1 per factor).
    - Stage 4: Alpha Leader Fallback (Balanced Selection).
    """

    @property
    def name(self) -> str:
        return "v3.4"

    def __init__(self):
        super().__init__()
        self.spec_version = "3.4"

    def select(self, returns, raw_candidates, stats_df, request):
        params = request.params.copy()
        last_resp = None
        for stage in [1, 2, 3, 4]:
            params["relaxation_stage"] = stage
            if stage == 2:
                t = self._get_active_thresholds(request)
                params.update({"entropy_max_threshold": min(1.0, t["entropy_max"] * 1.2), "efficiency_min_threshold": t["efficiency_min"] * 0.8})

            req = dataclasses.replace(request, params=params)
            resp = super().select(returns, raw_candidates, stats_df, req)
            last_resp = resp

            # Target pool size for differentiation
            if len(resp.winners) >= 15:
                return resp

        return last_resp
