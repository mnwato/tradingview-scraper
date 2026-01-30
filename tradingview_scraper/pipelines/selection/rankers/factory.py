from typing import Any, Dict, Optional

from tradingview_scraper.pipelines.selection.rankers.base import BaseRanker
from tradingview_scraper.pipelines.selection.rankers.mps import MPSRanker
from tradingview_scraper.pipelines.selection.rankers.regime import StrategyRegimeRanker
from tradingview_scraper.pipelines.selection.rankers.signal import SignalRanker


class RankerFactory:
    """
    Factory for creating Selection Ranker instances based on configuration.
    """

    @staticmethod
    def get_ranker(method: str, config: Optional[Dict[str, Any]] = None) -> BaseRanker:
        config = config or {}

        if method == "mps" or method == "alpha_score":
            return MPSRanker()

        if method == "signal":
            signal_name = config.get("signal", "recommend_ma")
            return SignalRanker(signal_name=signal_name)

        if method == "regime":
            strategy = config.get("strategy", "trend_following")
            return StrategyRegimeRanker(strategy=strategy)

        if method == "ensemble":
            from tradingview_scraper.pipelines.selection.rankers.ensemble import EnsembleRanker

            ensemble_config = config.get("ensemble", {})
            rankers_map = {}
            weights_map = {}

            for name, r_config in ensemble_config.items():
                r_method = r_config.get("method", "mps")
                rankers_map[name] = RankerFactory.get_ranker(r_method, r_config)
                weights_map[name] = float(r_config.get("weight", 1.0))

            return EnsembleRanker(rankers=rankers_map, weights=weights_map)

        # Default fallback
        return MPSRanker()
