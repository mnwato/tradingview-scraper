import json
import os

import numpy as np
import pandas as pd

from tradingview_scraper.risk import BarbellOptimizer

# Removed problematic import, we'll use manual tiers or factory if needed


def calculate_metrics(rets):
    ann = 252
    ar = rets.mean() * ann
    av = rets.std() * np.sqrt(ann)
    sharpe = ar / av if av != 0 else 0

    dr = rets[rets < 0]
    dv = dr.std() * np.sqrt(ann)
    sortino = ar / dv if dv != 0 else 0

    cum = (1 + rets).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax()
    max_dd = dd.min()
    calmar = ar / abs(max_dd) if max_dd != 0 else 0

    return {"Sharpe": sharpe, "Sortino": sortino, "Ann. Return": ar, "Ann. Vol": av, "Max DD": max_dd, "Calmar": calmar}


def run_experiment():
    # Load data
    returns_path = "data/lakehouse/portfolio_returns_raw.pkl"
    returns = pd.read_pickle(returns_path)

    with open("data/lakehouse/portfolio_candidates_raw.json", "r") as f:
        raw_candidates = json.load(f)

    # Tier 1: Current Selected (using the actual logic to be sure)
    # We'll use the winners from the most recent run
    with open("data/lakehouse/portfolio_candidates.json", "r") as f:
        tier1_symbols = [c["symbol"] for c in json.load(f)]

    # Tier 2: Broad (Top 25 by momentum)
    # Extract momentum from raw_candidates if available, else use returns mean
    mom = returns.mean().sort_values(ascending=False)
    tier2_symbols = mom.head(25).index.tolist()

    # Tier 3: Raw (Full pool)
    tier3_symbols = returns.columns.tolist()

    tiers = {"Tier 1 (Strict - 5)": tier1_symbols, "Tier 2 (Broad - 25)": tier2_symbols, "Tier 3 (Raw - 44+)": tier3_symbols}

    # We need antifragility stats for Barbell
    # For research, we'll calculate a simple proxy or use a constant if file missing
    stats_path = "data/lakehouse/selection_audit.json"
    if os.path.exists(stats_path):
        with open(stats_path, "r") as f:
            audit = json.load(f)
            # Create a stats DF
            stats_list = []
            alpha_scores = audit.get("selection", {}).get("metrics", {}).get("alpha_scores", {})
            for s, m in alpha_scores.items():
                stats_list.append({"Symbol": s, "Antifragility_Score": 1.0})  # Placeholder
            stats_df = pd.DataFrame(stats_list)
    else:
        stats_df = pd.DataFrame([{"Symbol": s, "Antifragility_Score": 1.0} for s in tier3_symbols])

    optimizer = BarbellOptimizer()

    results = []
    for name, symbols in tiers.items():
        # Clean returns for this subset
        sub_returns = returns[symbols].fillna(0.0)

        # Align stats_df
        sub_stats = stats_df[stats_df["Symbol"].isin(symbols)]

        # Optimize
        try:
            weights_df = optimizer.optimize(sub_returns, sub_stats, regime="NORMAL")
            weights = {row["Symbol"]: row["Weight"] for _, row in weights_df.iterrows()}

            # Backtest on actual returns (with NaNs for realistic handling if possible, or same as optimization)
            # Use same fillna for consistency in this research phase
            port_rets = pd.Series(0, index=returns.index)
            for s, w in weights.items():
                port_rets += sub_returns[s] * w

            metrics = calculate_metrics(port_rets)
            metrics["Tier"] = name
            metrics["Count"] = len(symbols)
            results.append(metrics)
        except Exception as e:
            print(f"Error optimizing {name}: {e}")

    if results:
        df = pd.DataFrame(results)
        print("\n--- Selection Alpha Tier Comparison (Barbell Profile) ---")
        print(df[["Tier", "Count", "Sharpe", "Sortino", "Ann. Return", "Ann. Vol", "Max DD", "Calmar"]].to_markdown(index=False))
    else:
        print("\nNo results generated.")


if __name__ == "__main__":
    run_experiment()
