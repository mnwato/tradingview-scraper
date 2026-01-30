import json

import numpy as np
import pandas as pd


def calculate_metrics(returns, weights):
    # returns: pd.Series of daily returns
    # weights: dict of {symbol: weight}

    # Calculate portfolio returns
    port_returns = pd.Series(0, index=returns.index)
    for symbol, weight in weights.items():
        if symbol in returns.columns:
            port_returns += returns[symbol] * weight

    # Ann factor (daily to yearly)
    ann_factor = 252

    # Metrics
    total_return = (1 + port_returns).prod() - 1
    ann_return = port_returns.mean() * ann_factor
    ann_vol = port_returns.std() * np.sqrt(ann_factor)
    sharpe = ann_return / ann_vol if ann_vol != 0 else 0

    # Sortino
    downside_returns = port_returns[port_returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(ann_factor)
    sortino = ann_return / downside_vol if downside_vol != 0 else 0

    # Max Drawdown
    cum_returns = (1 + port_returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns - running_max) / running_max
    max_dd = drawdown.min()

    return {"Ann. Return": ann_return, "Ann. Vol": ann_vol, "Sharpe": sharpe, "Sortino": sortino, "Max DD": max_dd, "Total Return": total_return}


if __name__ == "__main__":
    returns_df = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")
    with open("data/lakehouse/portfolio_optimized_v2.json", "r") as f:
        optimized = json.load(f)

    results = []
    for profile_name, profile_data in optimized["profiles"].items():
        weights = {asset["Symbol"]: asset["Weight"] for asset in profile_data["assets"]}
        metrics = calculate_metrics(returns_df, weights)
        metrics["Profile"] = profile_name
        results.append(metrics)

    # Add Benchmark (BTCUSDT)
    if "BINANCE:BTCUSDT" in returns_df.columns:
        btc_metrics = calculate_metrics(returns_df, {"BINANCE:BTCUSDT": 1.0})
        btc_metrics["Profile"] = "Benchmark (BTC)"
        results.append(btc_metrics)

    # Add Benchmark (SPY)
    if "AMEX:SPY" in returns_df.columns:
        spy_metrics = calculate_metrics(returns_df, {"AMEX:SPY": 1.0})
        spy_metrics["Profile"] = "Benchmark (SPY)"
        results.append(spy_metrics)

    df = pd.DataFrame(results)
    # Reorder columns
    cols = ["Profile", "Sharpe", "Sortino", "Ann. Return", "Ann. Vol", "Max DD", "Total Return"]
    df = df[cols].sort_values("Sharpe", ascending=False)

    print("Full Performance Metrics (Crypto Run 20260108-153730):")
    print(df.to_markdown(index=False))
