import logging
from typing import List, Tuple

import numpy as np

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.pipelines.selection.base import SelectionContext
from tradingview_scraper.pipelines.selection.filters.base import BaseFilter
from tradingview_scraper.settings import get_settings

logger = logging.getLogger(__name__)


@StageRegistry.register(id="selection.filter.predictability", name="Predictability Filter", description="Entropy and efficiency vetoes", category="selection", tags=["filter"])
class PredictabilityFilter(BaseFilter):
    """
    Predictability vetoes: Entropy, Efficiency, Kurtosis, and Stability filters.
    Includes Phase 156 Velocity vetoes.
    """

    @property
    def name(self) -> str:
        return "predictability"

    def apply(self, context: SelectionContext) -> Tuple[SelectionContext, List[str]]:
        vetoed = []
        s = get_settings()

        # Note: We check the setting here. If disabled, skip these vetoes.
        if not s.features.feat_predictability_vetoes:
            return context, []

        # Load thresholds from context params or global settings
        entropy_max = context.params.get("entropy_max_threshold", s.features.entropy_max_threshold)
        efficiency_min = context.params.get("efficiency_min_threshold", s.features.efficiency_min_threshold)
        hurst_min = context.params.get("hurst_random_walk_min", s.features.hurst_random_walk_min)
        hurst_max = context.params.get("hurst_random_walk_max", s.features.hurst_random_walk_max)

        # Standard: symbols as rows (index), metrics as columns
        metrics = context.inference_outputs

        for symbol in context.returns_df.columns:
            if symbol not in metrics.index:
                continue

            pe = metrics.loc[symbol, "entropy"] if "entropy" in metrics.columns else None
            er = metrics.loc[symbol, "efficiency"] if "efficiency" in metrics.columns else None
            h = metrics.loc[symbol, "hurst_clean"] if "hurst_clean" in metrics.columns else None
            kurt = metrics.loc[symbol, "kurtosis"] if "kurtosis" in metrics.columns else None
            stab = metrics.loc[symbol, "stability"] if "stability" in metrics.columns else 1.0
            roc = metrics.loc[symbol, "roc"] if "roc" in metrics.columns else 0.0
            vol_d = metrics.loc[symbol, "volatility_d"] if "volatility_d" in metrics.columns else 0.0

            # 1. Entropy Veto
            if pe is not None and not np.isnan(pe) and pe > entropy_max:
                vetoed.append(symbol)
                context.log_event("Filter", "Veto", {"symbol": symbol, "reason": f"High Entropy ({pe:.4f})"})
                continue

            # 2. Efficiency Veto
            if er is not None and not np.isnan(er) and er < efficiency_min:
                vetoed.append(symbol)
                context.log_event("Filter", "Veto", {"symbol": symbol, "reason": f"Low Efficiency ({er:.4f})"})
                continue

            # 3. Tail Risk (Kurtosis)
            if kurt is not None and not np.isnan(kurt) and kurt > 20.0:
                vetoed.append(symbol)
                context.log_event("Filter", "Veto", {"symbol": symbol, "reason": f"High Kurtosis ({kurt:.4f})"})
                continue

            # 4. Stability (Vol Cap)
            vol_val = 1.0 / (stab + 1e-9)
            if vol_val > 2.5:
                vetoed.append(symbol)
                context.log_event("Filter", "Veto", {"symbol": symbol, "reason": f"Excessive Volatility ({vol_val:.2%})"})
                continue

            # 5. Velocity Vetoes (Phase 156)
            if roc > 100.0 or roc < -80.0:
                vetoed.append(symbol)
                context.log_event("Filter", "Veto", {"symbol": symbol, "reason": f"Extreme Velocity (ROC={roc:.2f}%)"})
                continue

            if vol_d > 100.0:
                vetoed.append(symbol)
                context.log_event("Filter", "Veto", {"symbol": symbol, "reason": f"Extreme Daily Volatility ({vol_d:.2f}%)"})
                continue

            # 6. Hurst (Random Walk) Veto
            if h is not None and not np.isnan(h):
                # Is it a benchmark? Benchmarks are exempt.
                meta = next((c for c in context.raw_pool if c.get("symbol") == symbol), {})
                if not meta.get("is_benchmark", False):
                    if hurst_min < h < hurst_max:
                        vetoed.append(symbol)
                        context.log_event("Filter", "Veto", {"symbol": symbol, "reason": f"Random Walk (H={h:.4f})"})

        return context, vetoed
