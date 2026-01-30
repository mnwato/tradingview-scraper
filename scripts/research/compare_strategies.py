import logging

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("strategy_analysis")


def calculate_kpis(returns):
    """Calculates key performance indicators for a returns series."""
    vol = returns.std() * np.sqrt(252)
    cum_ret = (1 + returns).prod() - 1
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0

    # Downside Sortino
    negative_returns = returns[returns < 0]
    sortino = (returns.mean() / negative_returns.std()) * np.sqrt(252) if not negative_returns.empty else 0

    # Drawdown
    cum_prod = (1 + returns).cumprod()
    running_max = cum_prod.cummax()
    drawdown = (cum_prod - running_max) / running_max
    max_dd = drawdown.min()

    return {"Annualized_Vol": vol, "Total_Return": cum_ret, "Sharpe_Ratio": sharpe, "Sortino_Ratio": sortino, "Max_Drawdown": max_dd}


def analyze_strategies():
    # 1. Load Data
    returns_matrix = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")

    # Load Weights
    # MVP and RP are in one file
    with open("data/lakehouse/portfolio_optimized.json", "r") as f:
        mpt_weights = pd.read_json(f)

    # Barbell is in another
    with open("data/lakehouse/portfolio_barbell.json", "r") as f:
        barbell_weights = pd.read_json(f).set_index("Symbol")

    # 2. Reconstruct Portfolio Returns
    strategies = {}

    # A. Min Variance
    w_mv = mpt_weights["Min_Var_Weight"]
    strategies["Minimum Variance"] = np.dot(returns_matrix[w_mv.index], w_mv)

    # B. Risk Parity
    w_rp = mpt_weights["Risk_Parity_Weight"]
    strategies["Risk Parity"] = np.dot(returns_matrix[w_rp.index], w_rp)

    # C. Antifragile Barbell
    w_ab = barbell_weights["Weight"]
    # Ensure indices align
    aligned_returns = returns_matrix[w_ab.index]
    strategies["Antifragile Barbell"] = np.dot(aligned_returns, w_ab)

    # 3. Calculate Stats
    results = []
    for name, p_rets in strategies.items():
        kpis = calculate_kpis(pd.Series(p_rets))
        kpis["Strategy"] = name
        results.append(kpis)

    comparison_df = pd.DataFrame(results).set_index("Strategy")

    print("\n" + "=" * 100)
    print("PORTFOLIO STRATEGY COMPARISON (Research Window)")
    print("=" * 100)
    print(comparison_df.to_string())

    # 4. Regime Analysis: Tail Performance
    # Identify the worst 10% days for the average market
    market_avg = returns_matrix.mean(axis=1)
    tail_threshold = market_avg.quantile(0.10)
    bad_days_mask = market_avg <= tail_threshold

    print("\n" + "=" * 100)
    print("TAIL PERFORMANCE (Average return during bottom 10% market days)")
    print("=" * 100)

    tail_stats = {}
    for name, p_rets in strategies.items():
        tail_stats[name] = p_rets[bad_days_mask.values].mean()

    for name, val in tail_stats.items():
        print(f"  - {name:<20}: {val:>8.4%}")

    comparison_df.to_json("data/lakehouse/strategy_comparison.json")
    print("\nAnalysis saved to data/lakehouse/strategy_comparison.json")


if __name__ == "__main__":
    analyze_strategies()
