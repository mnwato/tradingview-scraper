import warnings
from tradingview_scraper.pipelines.selection.rankers.regime import StrategyRegimeRanker

warnings.warn("tradingview_scraper.selection_engines.ranker is deprecated. Please use tradingview_scraper.pipelines.selection.rankers.regime instead.", DeprecationWarning, stacklevel=2)

__all__ = ["StrategyRegimeRanker"]
