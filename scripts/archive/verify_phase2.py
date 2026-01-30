import logging

import pandas as pd

from tradingview_scraper.regime import MarketRegimeDetector
from tradingview_scraper.risk import BarbellOptimizer


def verify():
    logging.basicConfig(level=logging.INFO)

    # 1. Load Real Data
    try:
        returns = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")
        with open("data/lakehouse/antifragility_stats.json", "r") as f:
            import json

            stats = pd.DataFrame(json.load(f))
    except Exception as e:
        print(f"Skipping real data check (missing data/lakehouse artifacts): {e}")
        return

    detector = MarketRegimeDetector()
    optimizer = BarbellOptimizer()

    # 2. Test Detection
    regime = detector.detect_regime(returns)
    print(f"\nDetected Current Regime: {regime}")

    # 3. Test Adaptive Optimization
    print("\nRunning Adaptive Optimization...")
    portfolio = optimizer.optimize(returns, stats, regime=regime)

    # 4. Verify Structure
    core_w = portfolio[portfolio["Type"] == "CORE (Safe)"]["Weight"].sum()
    agg_w = portfolio[portfolio["Type"] == "AGGRESSOR (Antifragile)"]["Weight"].sum()

    print(f"Portfolio Structure: {core_w:.1%} Core, {agg_w:.1%} Aggressor")
    print(f"Top 5 Weights:\n{portfolio.head(5)[['Symbol', 'Weight']].to_string(index=False)}")


if __name__ == "__main__":
    verify()
