import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import numpy as np
import pandas as pd

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("hedge_detector")


def detect_hedge_anchors():
    # 1. Load Data
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    default_returns = str(run_dir / "data" / "returns_matrix.parquet")
    if not os.path.exists(default_returns):
        default_returns = "data/lakehouse/portfolio_returns.pkl"

    default_clusters = str(run_dir / "data" / "portfolio_clusters.json")
    if not os.path.exists(default_clusters):
        default_clusters = "data/lakehouse/portfolio_clusters.json"

    default_meta = str(run_dir / "data" / "portfolio_meta.json")
    if not os.path.exists(default_meta):
        default_meta = "data/lakehouse/portfolio_meta.json"

    returns_path = os.getenv("RETURNS_MATRIX", default_returns)
    clusters_path = os.getenv("CLUSTERS_FILE", default_clusters)
    meta_path = os.getenv("PORTFOLIO_META", default_meta)

    if not os.path.exists(returns_path) or not os.path.exists(clusters_path):
        logger.error(f"Required data missing: {returns_path} or {clusters_path}")
        return

    # Load returns (Parquet or Pickle)
    if returns_path.endswith(".parquet"):
        returns = pd.read_parquet(returns_path)
    else:
        with open(returns_path, "rb") as f_in:
            returns_raw = pd.read_pickle(f_in)
        if not isinstance(returns_raw, pd.DataFrame):
            returns = pd.DataFrame(returns_raw)
        else:
            returns = returns_raw

    with open(clusters_path, "r") as f:
        clusters = cast(Dict[str, List[str]], json.load(f))
    with open(meta_path, "r") as f:
        meta = cast(Dict[str, Any], json.load(f))

    # 2. Global Market Proxy
    market_rets = cast(pd.Series, returns.mean(axis=1))

    # 3. Cluster Benchmarks
    cluster_benchmarks = pd.DataFrame()
    for c_id, symbols in clusters.items():
        valid = [s for s in symbols if s in returns.columns]
        if valid:
            cluster_benchmarks[f"Cluster_{c_id}"] = returns[valid].mean(axis=1)

    # Identify Hedge Anchors (Negative correlation with Market or Clusters)
    results = []

    # General crypto hub detection based on asset class metadata
    crypto_cluster_key: Optional[str] = None
    for c_id, symbols in clusters.items():
        # Check if the cluster is predominantly crypto
        crypto_count = sum(1 for s in symbols if meta.get(s, {}).get("asset_class") == "CRYPTO")
        if crypto_count > 0 and (crypto_count / len(symbols)) > 0.5:
            crypto_cluster_key = f"Cluster_{c_id}"
            break

    for symbol in returns.columns:
        s_rets = cast(pd.Series, returns[symbol])

        # Correlation with Global Market
        market_corr = float(s_rets.corr(market_rets))

        crypto_corr = 0.0
        if crypto_cluster_key and crypto_cluster_key in cluster_benchmarks.columns:
            target_cluster_rets = cast(pd.Series, cluster_benchmarks[crypto_cluster_key])
            crypto_corr = float(s_rets.corr(target_cluster_rets))

        # Volatility
        # Use ddof=0 for numerical stability on short series
        vol = float(s_rets.std(ddof=0) * np.sqrt(252))

        results.append(
            {
                "Symbol": symbol,
                "Market_Correlation": market_corr,
                "Crypto_Correlation": crypto_corr,
                "Volatility": vol,
                "Market": meta.get(str(symbol), {}).get("market", "N/A"),
                "Description": meta.get(str(symbol), {}).get("description", "N/A"),
            }
        )

    df = pd.DataFrame(results)

    # Filter for potential hedges (negative correlation or very low correlation)
    hedges = df[df["Market_Correlation"] < 0.1].sort_values(by="Market_Correlation")

    print("\n" + "=" * 100)
    print("HEDGE ANCHOR DISCOVERY (Insurance Layer)")
    print("=" * 100)
    print("Identifying assets that provide negative correlation to systemic risk.")

    print("\n[Top 10 Global Hedge Anchors (Neg. Market Correlation)]")
    top_hedges = hedges.head(10)
    print(top_hedges[["Symbol", "Market_Correlation", "Volatility", "Market"]].to_string(index=False))

    if crypto_cluster_key:
        print(f"\n[Top 10 Crypto-Specific Hedges (Neg. Correlation with {crypto_cluster_key})]")
        crypto_hedges = df[df["Crypto_Correlation"] < 0.1].sort_values(by="Crypto_Correlation")
        top_crypto_hedges = crypto_hedges.head(10)
        print(top_crypto_hedges[["Symbol", "Crypto_Correlation", "Volatility", "Market"]].to_string(index=False))

    # Save results
    df.to_json("data/lakehouse/hedge_anchors.json")

    # Generate Markdown Summary
    md = ["# 🛡️ Hedge Anchor Discovery Report"]
    md.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append("\nAssets providing tail insurance via negative systemic correlation.")
    md.append("\n## 🌐 Global Hedges")
    md.append("| Symbol | Market Corr | Volatility | Market |")
    md.append("| :--- | :--- | :--- | :--- |")
    for _, r in top_hedges.iterrows():
        md.append(f"| `{r['Symbol']}` | {float(r['Market_Correlation']):.3f} | {float(r['Volatility']):.2%} | {r['Market']} |")

    settings = get_settings()
    settings.prepare_summaries_run_dir()
    output_path = settings.run_reports_dir / "portfolio" / "hedge_anchors.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    detect_hedge_anchors()
