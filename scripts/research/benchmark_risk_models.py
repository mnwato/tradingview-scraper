import logging

import numpy as np
import pandas as pd

from tradingview_scraper.portfolio_engines import CustomClusteredEngine, CVXPortfolioEngine, SkfolioEngine
from tradingview_scraper.portfolio_engines.base import EngineRequest

logging.basicConfig(level=logging.INFO)


def benchmark_risk_models():
    # 1. Fake Data with Structure
    # 4 assets: A, B (Highly Correlated), C, D (Uncorrelated)
    # A, B should be clustered.
    n_assets = 4
    dates = pd.date_range("2024-01-01", periods=200, tz="UTC")

    # Factors
    f1 = np.random.randn(200)
    f2 = np.random.randn(200)
    f3 = np.random.randn(200)

    # Assets
    # A, B driven by F1 (High Corr)
    # C driven by F2
    # D driven by F3
    df = pd.DataFrame(index=dates)
    df["A"] = f1 + np.random.randn(200) * 0.1
    df["B"] = f1 + np.random.randn(200) * 0.1
    df["C"] = f2 + np.random.randn(200) * 0.1
    df["D"] = f3 + np.random.randn(200) * 0.1

    # Scale Volatility: A=High, B=High, C=Med, D=Low
    df["A"] *= 0.02
    df["B"] *= 0.02
    df["C"] *= 0.015
    df["D"] *= 0.01

    returns = df
    clusters = {"1": ["A", "B"], "2": ["C"], "3": ["D"]}

    # 2. Risk Parity Benchmark
    print("\n--- RISK PARITY (ERC) ---")
    req_rp = EngineRequest(profile="risk_parity", cluster_cap=1.0)

    engines = {
        "Custom": CustomClusteredEngine(),
        "CVXPortfolio": CVXPortfolioEngine(),
    }

    # Check if skfolio is available
    if SkfolioEngine.is_available():
        engines["Skfolio"] = SkfolioEngine()

    for name, eng in engines.items():
        try:
            resp = eng.optimize(returns=returns, clusters=clusters, meta={}, stats=None, request=req_rp)
            w = resp.weights.set_index("Symbol")["Weight"].sort_index()
            if w.empty:
                print(f"{name}: Empty weights. Warnings: {resp.warnings}")
            else:
                print(f"{name}:\n{w.values.round(4)}")
        except Exception as e:
            print(f"{name}: Failed ({e})")

    # 3. HRP Benchmark
    print("\n--- HRP (Hierarchical) ---")
    req_hrp = EngineRequest(profile="hrp", cluster_cap=1.0)

    for name, eng in engines.items():
        if name == "CVXPortfolio":
            continue  # Delegates to Custom anyway
        try:
            resp = eng.optimize(returns=returns, clusters=clusters, meta={}, stats=None, request=req_hrp)
            w = resp.weights.set_index("Symbol")["Weight"].sort_index()
            print(f"{name}:\n{w.values.round(4)}")
        except Exception as e:
            print(f"{name}: Failed ({e})")


if __name__ == "__main__":
    benchmark_risk_models()
