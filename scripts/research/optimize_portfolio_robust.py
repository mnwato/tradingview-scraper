import json
import logging

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robust_optimizer")


def calculate_semi_variance(weights, returns):
    """Calculates downside semi-variance (volatility of negative returns only)."""
    port_returns = np.dot(returns, weights)
    # Filter for negative returns only
    downside_returns = port_returns[port_returns < 0]
    if len(downside_returns) == 0:
        return 0
    return np.std(downside_returns) * np.sqrt(252)


def calculate_liquidity_penalty(weights, volume_data, port_value=1000000):
    """
    Penalizes positions that exceed 1% of average daily volume.
    port_value: Nominal value of the portfolio to be deployed.
    """
    # Weight * portfolio_value / average_daily_volume
    participation_rate = (weights * port_value) / volume_data
    # Square the excess participation to penalize large concentrations heavily
    penalty = np.sum(np.square(np.maximum(0, participation_rate - 0.01)))
    return penalty * 100  # Scaling factor


def robust_objective(weights, returns, volume_data, alpha_weights):
    vol = calculate_semi_variance(weights, returns)
    liq_penalty = calculate_liquidity_penalty(weights, volume_data)

    # Alpha Benefit (Negative of return to maximize)
    # Scale initial alpha by trend strength (ADX)
    alpha_score = np.sum(weights * alpha_weights)

    # Goal: Minimize (Downside Vol + Liquidity Penalty) - Alpha Benefit
    return vol + liq_penalty - (alpha_score * 0.1)


def optimize_robust_portfolio():
    # 1. Load Data
    returns = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")
    with open("data/lakehouse/portfolio_meta.json", "r") as f:
        meta = json.load(f)

    # Filter symbols
    returns = returns.loc[:, (returns != 0).any(axis=0)]
    symbols = returns.columns
    n_assets = len(symbols)

    logger.info(f"Optimizing Robust Portfolio for {n_assets} assets...")

    # 2. Extract Alpha/Liquidity Metrics
    # volume_data: Map of Value.Traded
    # alpha_weights: Map of ADX (normalized)
    volumes = np.array([meta[s]["value_traded"] for s in symbols])
    # Handle zero volumes to avoid div by zero
    volumes = np.maximum(volumes, 1.0)

    adx_scores = np.array([meta[s]["adx"] for s in symbols])
    # Normalize ADX to 0-1 range for weighting
    alpha_weights = adx_scores / 100.0

    # 3. Optimization Setup
    init_weights = np.array([1.0 / n_assets] * n_assets)
    bounds = tuple((0.0, 0.2) for _ in range(n_assets))  # Max 20% per asset for diversification
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

    # 4. Solve
    logger.info("Solving Robust Portfolio (Semi-Variance + Liquidity Penalty)...")
    res = minimize(robust_objective, init_weights, args=(returns.values, volumes, alpha_weights), method="SLSQP", bounds=bounds, constraints=constraints)

    # 5. Results
    results_df = pd.DataFrame(index=symbols)
    results_df["Weight"] = res.x
    results_df["Signal"] = [meta[s]["direction"] for s in symbols]
    results_df["ADX"] = [meta[s]["adx"] for s in symbols]
    results_df["Value_Traded"] = [meta[s]["value_traded"] for s in symbols]

    top_portfolio = results_df[results_df["Weight"] > 0.005].sort_values("Weight", ascending=False)

    print("\n" + "=" * 80)
    print("ROBUST PORTFOLIO OPTIMIZATION RESULTS")
    print("=" * 80)
    print(f"Objective Value: {res.fun:.4f}")
    print(f"Asset Count    : {len(top_portfolio)}")
    print("\nTop Allocations:")
    print(top_portfolio[["Signal", "Weight", "ADX", "Value_Traded"]].head(20).to_string())

    # Save optimized portfolio
    top_portfolio.to_json("data/lakehouse/portfolio_robust.json")
    print("\nSaved to data/lakehouse/portfolio_robust.json")


if __name__ == "__main__":
    optimize_robust_portfolio()
