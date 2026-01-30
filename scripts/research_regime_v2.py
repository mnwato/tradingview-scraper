import logging
import os
from typing import cast

import pandas as pd

from tradingview_scraper.regime import MarketRegimeDetector

logging.basicConfig(level=logging.INFO)


def research_regime():
    from tradingview_scraper.settings import get_settings

    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    default_returns = str(run_dir / "data" / "returns_matrix.parquet")
    if not os.path.exists(default_returns):
        default_returns = "data/lakehouse/portfolio_returns.pkl"

    returns_path = os.getenv("RETURNS_MATRIX", default_returns)
    if not os.path.exists(returns_path):
        print(f"Returns matrix missing: {returns_path}")
        return

    # Load returns (Parquet or Pickle)
    if returns_path.endswith(".parquet"):
        returns = pd.read_parquet(returns_path)
    else:
        returns = cast(pd.DataFrame, pd.read_pickle(returns_path))
    detector = MarketRegimeDetector()

    # Test full series
    regime = detector.detect_regime(returns)
    print(f"\nFinal Identified Regime: {regime}")

    # Test sub-slices to see if it changes
    # Recent 20 days
    recent = returns.tail(20)
    print(f"Recent 20d Regime: {detector.detect_regime(recent)}")

    # Middle slice
    if len(returns) > 100:
        middle = returns.iloc[20:80]
        print(f"Middle 60d Regime: {detector.detect_regime(middle)}")


if __name__ == "__main__":
    research_regime()
