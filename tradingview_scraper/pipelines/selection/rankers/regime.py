import logging
from typing import Any, Dict, List

import pandas as pd

from tradingview_scraper.regime import MarketRegimeDetector

from tradingview_scraper.pipelines.selection.rankers.base import BaseRanker
from tradingview_scraper.pipelines.selection.base import SelectionContext

logger = logging.getLogger(__name__)


class StrategyRegimeRanker(BaseRanker):
    """
    Ranks assets based on their suitability for a specific strategy given their current regime.
    Part of Phase 270 (Strategy-Specific Selection).
    """

    def __init__(self, strategy: str = "trend_following", enable_audit_log: bool = False):
        self.strategy = strategy
        self.detector = MarketRegimeDetector(enable_audit_log=enable_audit_log)

    def rank(self, candidates: List[str], context: SelectionContext, ascending: bool = False) -> List[str]:
        """
        Sorts the candidate list based on strategy-regime fit.
        Implements BaseRanker interface.
        """
        # 1. Map candidates to metadata
        symbol_to_meta = {c["symbol"]: c for c in context.winners if "symbol" in c}
        cand_meta = [symbol_to_meta[s] for s in candidates if s in symbol_to_meta]

        # 2. Use specialized rank logic
        ranked_meta = self.rank_metadata(cand_meta, context.returns_df, self.strategy)

        # 3. Return sorted IDs
        sorted_ids = [m["symbol"] for m in ranked_meta]

        if ascending:
            sorted_ids.reverse()

        return sorted_ids

    def rank_metadata(self, candidates: List[Dict[str, Any]], returns: pd.DataFrame, strategy: str = "trend_following") -> List[Dict[str, Any]]:
        """
        Calculates a 'Strategy Fit Score' for each candidate.

        Args:
            candidates: List of candidate metadata dicts.
            returns: DataFrame of recent asset returns.
            strategy: 'trend_following' | 'mean_reversion' | 'breakout'

        Returns:
            List of candidates sorted by rank_score descending.
        """
        results = []
        for cand in candidates:
            symbol = cand.get("symbol")
            if not symbol or symbol not in returns.columns:
                continue

            series = returns[symbol].dropna()
            if len(series) < 64:  # Min window for spectral analysis
                continue

            # 1. Detect Asset-Level Regime
            try:
                # Wrap in DF as detector expects wide format for mean calc
                df_slice = pd.DataFrame({symbol: series})
                regime_label, regime_score, quadrant = self.detector.detect_regime(df_slice)

                # 2. Extract Structural Metrics
                # Hurst Exponent (0.5 = Random, >0.5 = Trending, <0.5 = Mean Reverting)
                hurst = self.detector._hurst_exponent(series.values)

                # Volatility Clustering (Persistence of variance)
                vc = self.detector._volatility_clustering(series.values)
            except Exception as e:
                logger.warning(f"Failed to rank {symbol}: {e}")
                continue

            # 3. Calculate Fit Score
            rank_score = 0.0

            if strategy == "trend_following":
                # Priority 1: Trending Quadrants
                if quadrant in ["INFLATIONARY_TREND", "EXPANSION"]:
                    rank_score += 0.6
                elif quadrant == "STAGNATION":
                    rank_score -= 0.3
                elif quadrant == "CRISIS":
                    # Crisis is high vol, often trending but potentially reversing
                    rank_score += 0.2

                # Priority 2: High Hurst (Persistence)
                if hurst > 0.55:
                    # Scale based on how much it exceeds 0.55
                    rank_score += min(0.4, (hurst - 0.55) * 2.0)
                elif hurst < 0.45:
                    rank_score -= 0.4

                # Priority 3: Volatility Clustering (Trends usually cluster vol)
                if vc > 0.5:
                    rank_score += 0.1

            elif strategy == "mean_reversion":
                # Priority 1: Mean Reverting / Ranging Quadrants
                if quadrant in ["STAGNATION", "NORMAL"]:
                    rank_score += 0.6
                elif quadrant == "INFLATIONARY_TREND":
                    rank_score -= 0.6  # Stay away from runaway trends
                elif quadrant == "CRISIS":
                    rank_score += 0.4  # Potential for mean reversion from extremes

                # Priority 2: Low Hurst (Anti-persistence)
                if hurst < 0.45:
                    rank_score += min(0.4, (0.45 - hurst) * 2.0)
                elif hurst > 0.55:
                    rank_score -= 0.4

                # Priority 3: Quietness (Oscillations are cleaner in quiet)
                if regime_label == "QUIET":
                    rank_score += 0.2

            # 4. Enrich and Collect
            updated_cand = cand.copy()
            updated_cand.update({"rank_score": float(rank_score), "asset_regime": regime_label, "asset_quadrant": quadrant, "asset_hurst": float(hurst), "asset_vc": float(vc)})
            results.append(updated_cand)

        # Sort by rank_score descending
        return sorted(results, key=lambda x: x["rank_score"], reverse=True)
