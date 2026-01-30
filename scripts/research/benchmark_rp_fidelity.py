import logging

import numpy as np
import pandas as pd

from tradingview_scraper.portfolio_engines import CustomClusteredEngine, CVXPortfolioEngine
from tradingview_scraper.portfolio_engines.base import EngineRequest

logging.basicConfig(level=logging.INFO)


def benchmark_rp():
    # 1. Fake Data
    n_assets = 5
    dates = pd.date_range("2024-01-01", periods=100, tz="UTC")
    # Make volatilities different to test RP
    vols = np.linspace(0.01, 0.05, n_assets)
    returns = pd.DataFrame(np.random.randn(100, n_assets) * vols, index=dates, columns=pd.Index([f"A{i}" for i in range(n_assets)]))

    clusters = {f"C{i}": [f"A{i}"] for i in range(n_assets)}

    req = EngineRequest(profile="risk_parity", cluster_cap=1.0)

    # 2. Run Custom
    print("\n--- Custom Engine (Reference) ---")
    custom = CustomClusteredEngine()
    resp_cust = custom.optimize(returns=returns, clusters=clusters, meta={}, stats=None, request=req)
    w_cust = resp_cust.weights.set_index("Symbol")["Weight"].sort_index()
    print(w_cust)

    # 3. Run CVXPortfolio (Native)
    print("\n--- CVXPortfolio Engine (Native) ---")
    cvx_eng = CVXPortfolioEngine()
    resp_cvx = cvx_eng.optimize(returns=returns, clusters=clusters, meta={}, stats=None, request=req)
    w_cvx = resp_cvx.weights.set_index("Symbol")["Weight"].sort_index()
    print(w_cvx)

    # 4. Compare
    diff = (w_cust - w_cvx).abs().sum()
    print(f"\nTotal Absolute Difference: {diff:.6f}")
    if diff < 1e-2:
        print("PASS: Engines match.")
    else:
        print("FAIL: Engines diverge.")


if __name__ == "__main__":
    benchmark_rp()
