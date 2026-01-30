import logging

import pandas as pd

from tradingview_scraper.risk import BarbellOptimizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("barbell_optimizer")


def build_barbell_portfolio():
    # 1. Load Data
    returns = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")
    returns = returns.loc[:, (returns != 0).any(axis=0)]

    with open("data/lakehouse/antifragility_stats.json", "r") as f:
        stats = pd.read_json(f)

    # 2. SELECTION & OPTIMIZATION via Risk Module
    optimizer = BarbellOptimizer()
    # Assume NORMAL regime for this standalone script
    df = optimizer.optimize(returns, stats, regime="NORMAL")

    print("\n" + "=" * 80)
    print("ANTIFRAGILE BARBELL PORTFOLIO (Taleb Strategy)")
    print("=" * 80)
    print("Structure: 90% Diverse Core | 10% Convex Aggressors")

    print("\nTop 15 Allocations:")
    print(df.head(15).to_string(index=False))

    print("\n[Aggressor Bucket - Tail Gain Engines]")
    print(df[df["Type"] == "AGGRESSOR (Antifragile)"].to_string(index=False))

    df.to_json("data/lakehouse/portfolio_barbell.json")
    print("\nSaved to data/lakehouse/portfolio_barbell.json")


if __name__ == "__main__":
    build_barbell_portfolio()
