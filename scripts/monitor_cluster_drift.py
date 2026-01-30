import json
import logging
import os
from datetime import datetime
from typing import Dict, List, cast

import numpy as np
import pandas as pd
from scipy.spatial.distance import cosine

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cluster_drift")


def monitor_drift():
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

    returns_path = os.getenv("RETURNS_MATRIX", default_returns)
    clusters_path = os.getenv("CLUSTERS_FILE", default_clusters)

    if not os.path.exists(returns_path) or not os.path.exists(clusters_path):
        logger.error(f"Required data missing: {returns_path} or {clusters_path}")
        return

    # Load returns (Parquet or Pickle)
    if returns_path.endswith(".parquet"):
        returns = pd.read_parquet(returns_path)
    else:
        returns = cast(pd.DataFrame, pd.read_pickle(returns_path))

    with open(clusters_path, "r") as f:
        clusters = cast(Dict[str, List[str]], json.load(f))

    if len(returns) < 40:
        logger.warning("Insufficient data for drift analysis (need at least 40 days).")
        return

    # 2. Split returns into two periods (Benchmark vs Recent)
    mid = len(returns) // 2
    period_1 = returns.iloc[:mid]
    period_2 = returns.iloc[mid:]

    logger.info(f"Analyzing drift: Period 1 ({len(period_1)}d) vs Period 2 ({len(period_2)}d)")

    # 3. Calculate Drift per Cluster
    drift_results = []

    for c_id, symbols in clusters.items():
        valid = [s for s in symbols if s in returns.columns]
        if len(valid) < 2:
            continue

        # Intra-cluster correlation matrices
        corr_1 = period_1[valid].corr().values
        corr_2 = period_2[valid].corr().values

        # Flatten upper triangles to vectors
        tri_idx = np.triu_indices(len(valid), k=1)
        vec_1 = corr_1[tri_idx]
        vec_2 = corr_2[tri_idx]

        # Stability = Cosine similarity between correlation vectors
        # Drift = 1 - Similarity
        if np.all(vec_1 == 0) or np.all(vec_2 == 0):
            similarity = 1.0
        else:
            # Handle potential NaNs
            vec_1 = np.nan_to_num(vec_1)
            vec_2 = np.nan_to_num(vec_2)
            if np.any(vec_1) and np.any(vec_2):
                similarity = 1.0 - cosine(vec_1, vec_2)
            else:
                similarity = 1.0

        drift = 1.0 - similarity

        # Change in average correlation
        avg_corr_1 = float(np.mean(vec_1))
        avg_corr_2 = float(np.mean(vec_2))
        corr_diff = avg_corr_2 - avg_corr_1

        drift_results.append(
            {
                "Cluster_ID": c_id,
                "Drift_Score": drift,
                "Similarity": similarity,
                "Avg_Corr_P1": avg_corr_1,
                "Avg_Corr_P2": avg_corr_2,
                "Corr_Delta": corr_diff,
                "Size": len(valid),
                "Lead_Asset": valid[0],
            }
        )

    if not drift_results:
        logger.warning("No clusters with multiple assets found. Skipping drift analysis.")
        return

    df = pd.DataFrame(drift_results).sort_values(by="Drift_Score", ascending=False)

    print("\n" + "=" * 100)
    print("CLUSTER STABILITY & DRIFT MONITOR")
    print("=" * 100)
    print("High drift indicates that assets in a cluster are losing their statistical linkage.")

    print("\n[Top 5 Most Drifting (Unstable) Clusters]")
    print(df.head(5)[["Cluster_ID", "Drift_Score", "Corr_Delta", "Size", "Lead_Asset"]].to_string(index=False))

    print("\n[Top 5 Most Stable Clusters]")
    print(df.tail(5)[["Cluster_ID", "Drift_Score", "Corr_Delta", "Size", "Lead_Asset"]].to_string(index=False))

    # Save results
    json_out = run_dir / "data" / "cluster_drift.json"
    os.makedirs(json_out.parent, exist_ok=True)
    df.to_json(str(json_out))

    # Generate Markdown Summary
    md = ["# 🔄 Cluster Drift & Stability Report"]
    md.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append("\nMeasuring the temporal stability of hierarchical risk buckets.")

    md.append("\n## 🚩 High Drift Alerts")
    high_drift = df[df["Drift_Score"] > 0.3]
    if not high_drift.empty:
        md.append("| Cluster | Drift Score | Avg Corr Change | Size |")
        md.append("| :--- | :--- | :--- | :--- |")
        for _, r in high_drift.iterrows():
            md.append(f"| **Cluster {r['Cluster_ID']}** | {r['Drift_Score']:.3f} | {r['Corr_Delta']:+.3f} | {r['Size']} |")
    else:
        md.append("✅ No high drift detected. Clusters are statistically stable.")

    output_dir = get_settings().prepare_summaries_run_dir()
    output_path = output_dir / "cluster_drift.md"
    with open(output_path, "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    monitor_drift()
