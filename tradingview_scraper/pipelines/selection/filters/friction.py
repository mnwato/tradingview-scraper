import logging
from typing import List, Tuple

import numpy as np

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.pipelines.selection.base import SelectionContext
from tradingview_scraper.pipelines.selection.filters.base import BaseFilter
from tradingview_scraper.settings import get_settings

logger = logging.getLogger(__name__)


@StageRegistry.register(id="selection.filter.friction", name="Friction Filter", description="Execution cost veto (ECI)", category="selection", tags=["filter"])
class FrictionFilter(BaseFilter):
    """
    Execution Cost Index (ECI) veto: filters assets with excessive trading costs relative to alpha.
    """

    @property
    def name(self) -> str:
        return "friction"

    def apply(self, context: SelectionContext) -> Tuple[SelectionContext, List[str]]:
        vetoed = []
        s = get_settings()

        eci_hurdle = context.params.get("eci_hurdle", 0.02)

        candidate_map = {c["symbol"]: c for c in context.raw_pool if "symbol" in c}
        # We need momentum and volatility for ECI calculation
        # Standard: symbols as rows (index), metrics as columns
        metrics = context.inference_outputs

        for symbol in context.returns_df.columns:
            if symbol not in metrics.index:
                continue

            mom = metrics.loc[symbol, "momentum"] if "momentum" in metrics.columns else 0.0
            vol = metrics.loc[symbol, "stability"] if "stability" in metrics.columns else 1.0  # Stability is 1/vol

            vol_abs = 1.0 / (vol + 1e-9)

            meta = candidate_map.get(symbol, {})
            adv = float(meta.get("value_traded") or 1e8)

            # Formula: vol * sqrt(1e6 / ADV)
            eci_raw = float(vol_abs * np.sqrt(1e6 / (adv if adv > 0 else 1e8)))

            # Apply hurdle
            # (Logic from v3_mps.py)
            if (mom - eci_raw) < eci_hurdle and not (mom > 1.0 and (mom - eci_raw) >= (eci_hurdle * 1.25)):
                vetoed.append(symbol)
                context.log_event("Filter", "Veto", {"symbol": symbol, "reason": f"High friction (ECI={eci_raw:.4f})", "net_alpha": float(mom - eci_raw)})

        return context, vetoed
