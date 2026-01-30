import argparse
import json
import logging
import os
from typing import Any, Dict, List, cast

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import squareform

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("subcluster_analysis")


def analyze_subcluster(cluster_id: str, clusters_path: str, meta_path: str, returns_path: str, output_dir: str, threshold: float = 0.2):
    if not os.path.exists(clusters_path) or not os.path.exists(meta_path) or not os.path.exists(returns_path):
        logger.error("Required files missing for subcluster analysis.")
        return

    with open(clusters_path, "r") as f:
        clusters = cast(Dict[str, List[str]], json.load(f))
    with open(meta_path, "r") as f:
        meta = cast(Dict[str, Any], json.load(f))
    returns_raw = pd.read_pickle(returns_path)
    returns = pd.DataFrame(returns_raw)

    if cluster_id not in clusters:
        logger.error(f"Cluster {cluster_id} not found in {clusters_path}")
        return

    symbols = [s for s in clusters[cluster_id] if s in returns.columns]
    if len(symbols) < 2:
        logger.error(f"Cluster {cluster_id} has too few valid symbols for sub-clustering.")
        return

    sub_rets = returns[symbols]
    corr = sub_rets.corr()

    # Hierarchical Linkage
    dist_matrix = np.sqrt(0.5 * (1 - corr.values.clip(-1, 1)))
    dist_matrix = (dist_matrix + dist_matrix.T) / 2
    np.fill_diagonal(dist_matrix, 0)

    condensed = squareform(dist_matrix, checks=False)
    # Using keyword arguments to appease linter
    link = sch.linkage(y=condensed, method="average")

    # Flat sub-clusters
    sub_cluster_assignments = sch.fcluster(Z=link, t=threshold, criterion="distance")

    sub_clusters: Dict[int, List[str]] = {}
    for sym, sc_id in zip(symbols, sub_cluster_assignments):
        sc_id_int = int(sc_id)
        if sc_id_int not in sub_clusters:
            sub_clusters[sc_id_int] = []
        sub_clusters[sc_id_int].append(sym)

    # Generate Report
    report = []
    report.append(f"# 🔍 Sub-Cluster Analysis: Cluster {cluster_id}")
    report.append(f"**Parent Cluster:** {cluster_id}")
    report.append(f"**Total Symbols:** {len(symbols)}")
    report.append(f"**Sub-Clusters Found:** {len(sub_clusters)} (at threshold {threshold})")
    report.append("\n---")

    report.append("## 📊 Sub-Clusters Overview")
    report.append("| Sub-Cluster | Size | Primary Assets | Avg Vol |")
    report.append("| :--- | :--- | :--- | :--- |")

    summary_data = []
    for sc_id, sc_symbols in sub_clusters.items():
        sc_rets = sub_rets[sc_symbols]
        mean_rets = sc_rets.mean(axis=1)
        if isinstance(mean_rets, pd.Series):
            std_val = float(mean_rets.std())
        else:
            std_val = float(np.std(mean_rets))

        vol = std_val * np.sqrt(252) if not np.isnan(std_val) else 0.0

        leads = ", ".join([f"`{s}`" for s in sc_symbols[:3]])
        if len(sc_symbols) > 3:
            leads += " ..."

        summary_data.append({"id": sc_id, "size": len(sc_symbols), "leads": leads, "vol": vol, "symbols": sc_symbols})

    for s in sorted(summary_data, key=lambda x: x["size"], reverse=True):
        report.append(f"| {s['id']} | {s['size']} | {s['leads']} | {s['vol']:.2%} |")

    for s in sorted(summary_data, key=lambda x: x["size"], reverse=True):
        report.append(f"\n### 📦 Sub-Cluster {s['id']}")
        report.append(f"- **Size:** {s['size']} assets")
        report.append("- **Assets:** " + ", ".join([f"`{sym}`" for sym in s["symbols"]]))

        report.append("\n#### 📋 Asset Details")
        report.append("| Symbol | Description | Market | Direction |")
        report.append("| :--- | :--- | :--- | :--- |")
        for sym in s["symbols"]:
            s_meta = meta.get(sym, {})
            report.append(f"| `{sym}` | {s_meta.get('description', 'N/A')} | {s_meta.get('market', 'UNKNOWN')} | {s_meta.get('direction', 'LONG')} |")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"subcluster_{cluster_id}.md")
    with open(output_path, "w") as f:
        f.write("\n".join(report))

    logger.info(f"✅ Sub-cluster analysis for Cluster {cluster_id} generated at: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a specific cluster's internal hierarchy")
    parser.add_argument("--cluster", required=True, help="Cluster ID to analyze")
    parser.add_argument("--threshold", type=float, default=0.2, help="Distance threshold for sub-clustering")
    args = parser.parse_args()

    output_dir = get_settings().prepare_summaries_run_dir()
    analyze_subcluster(args.cluster, "data/lakehouse/portfolio_clusters.json", "data/lakehouse/portfolio_meta.json", "data/lakehouse/portfolio_returns.pkl", str(output_dir), threshold=args.threshold)
