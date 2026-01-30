import json
import logging
import os
from typing import cast

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.manifold import MDS

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("factor_map")


def generate_factor_map():
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
    stats_path = os.getenv("ANTIFRAGILITY_STATS", str(run_dir / "data" / "antifragility_stats.json"))
    output_dir = settings.run_plots_dir / "risk"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "factor_map.png"

    if not os.path.exists(returns_path) or not os.path.exists(clusters_path):
        logger.error(f"Required data missing for factor map: {returns_path} or {clusters_path}")
        return

    # Load returns (Parquet or Pickle)
    if returns_path.endswith(".parquet"):
        returns = pd.read_parquet(returns_path)
    else:
        with open(returns_path, "rb") as f:
            returns = cast(pd.DataFrame, pd.read_pickle(f))

    with open(clusters_path, "r") as f:
        clusters = json.load(f)

    stats_df = None
    if os.path.exists(stats_path):
        stats_df = pd.read_json(stats_path)

    # 1. Calculate Cluster Centroids (Average Returns)
    centroids = pd.DataFrame()
    cluster_labels = []
    cluster_fragility = []

    for c_id, symbols in clusters.items():
        valid = [s for s in symbols if s in returns.columns]
        if not valid:
            continue

        # Simple average for centroid
        centroids[f"C{c_id}"] = returns[valid].mean(axis=1)
        cluster_labels.append(f"Cluster {c_id}")

        if stats_df is not None:
            c_stats = stats_df[stats_df["Symbol"].isin(valid)]
            cluster_fragility.append(c_stats["Fragility_Score"].mean() if not c_stats.empty else 1.0)
        else:
            cluster_fragility.append(1.0)

    if centroids.empty:
        logger.error("No valid clusters found.")
        return

    # 2. Correlation Distance
    corr = centroids.corr()
    dist = np.sqrt(0.5 * (1 - corr.clip(-1, 1)))

    # 3. MDS Projection to 2D
    # Explicitly set n_init and init to suppress FutureWarnings from newer sklearn versions.
    # 'dissimilarity' is deprecated in favor of 'metric' in sklearn 1.4+.
    mds = MDS(
        n_components=2,
        metric="precomputed",
        n_init=4,
        init="random",
        random_state=42,
        normalized_stress="auto",
    )
    coords = mds.fit_transform(dist.values)

    # 4. Plotting
    plt.figure(figsize=(12, 10))

    # Color by fragility
    scatter = plt.scatter(
        coords[:, 0],
        coords[:, 1],
        s=[500 + 200 * f for f in cluster_fragility],  # size by fragility
        c=cluster_fragility,
        cmap="RdYlGn_r",
        alpha=0.6,
        edgecolors="white",
    )

    # Annotate labels
    for i, label in enumerate(cluster_labels):
        plt.annotate(label, (coords[i, 0], coords[i, 1]), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9, fontweight="bold")

    plt.title("Hierarchical Factor Proximity Map (MDS)", fontsize=16)
    plt.xlabel("MDS Dimension 1")
    plt.ylabel("MDS Dimension 2")
    plt.grid(True, linestyle="--", alpha=0.3)

    cbar = plt.colorbar(scatter)
    cbar.set_label("Average Fragility Score (Red = High Risk)")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    logger.info(f"✅ Factor Map saved to: {output_path}")


if __name__ == "__main__":
    generate_factor_map()
