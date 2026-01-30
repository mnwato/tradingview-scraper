import json
import logging
import os
from typing import Any, Dict, List, cast

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
import seaborn as sns
from scipy.spatial.distance import squareform

from tradingview_scraper.risk import VolatilityClusterer
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cluster_analysis")


def perform_subclustering(symbols: List[str], returns: pd.DataFrame, threshold: float = 0.2) -> Dict[int, List[str]]:
    """
    Identifies sub-clusters within a set of symbols using hierarchical linkage.
    """
    if len(symbols) < 2:
        return {1: symbols}

    sub_rets = cast(pd.DataFrame, returns[symbols])

    # Filter for non-constant returns to avoid divide by zero in correlation
    non_constant = sub_rets.columns[sub_rets.std() > 1e-12].tolist()
    if len(non_constant) < 2:
        return {1: symbols}

    sub_rets_df = cast(pd.DataFrame, sub_rets[non_constant])
    corr = sub_rets_df.corr()

    # Hierarchical Linkage
    dist_matrix = np.sqrt(0.5 * (1 - corr.values.clip(-1, 1)))
    dist_matrix = (dist_matrix + dist_matrix.T) / 2
    np.fill_diagonal(dist_matrix, 0)

    condensed = squareform(dist_matrix, checks=False)
    link = sch.linkage(condensed, method="average")

    # Flat sub-clusters
    sub_cluster_assignments = sch.fcluster(link, t=threshold, criterion="distance")

    sub_clusters: Dict[int, List[str]] = {}
    for sym, sc_id in zip(non_constant, sub_cluster_assignments):
        sc_id_int = int(sc_id)
        if sc_id_int not in sub_clusters:
            sub_clusters[sc_id_int] = []
        sub_clusters[sc_id_int].append(sym)

    # Add constant symbols to a fallback cluster
    if len(non_constant) < len(symbols):
        fallback_id = max(sub_clusters.keys()) + 1 if sub_clusters else 1
        sub_clusters[fallback_id] = [s for s in symbols if s not in non_constant]

    return sub_clusters


def visualize_volatility_clusters(returns: pd.DataFrame, output_path: str) -> Any:
    """
    Generates a clustermap based on volatility co-movement (Log-Vol Correlation).
    Returns the linkage matrix for further analysis.
    """
    if returns.empty or returns.shape[1] < 2:
        return None

    logger.info(f"Generating volatility clustermap for {len(returns.columns)} assets...")

    clusterer = VolatilityClusterer(window=20)
    log_vol = clusterer.calculate_volatility_series(returns)
    if log_vol.empty:
        return None

    # Filter for non-constant volatility to avoid division by zero
    non_constant = log_vol.columns[log_vol.std() > 1e-12].tolist()
    if len(non_constant) < 2:
        return None

    vol_corr = log_vol[non_constant].corr().fillna(0.0)

    # Emerald-to-Purple palette for volatility (risk-focused)
    cmap = sns.color_palette("viridis", as_cmap=True)

    g = sns.clustermap(
        vol_corr,
        method="ward",
        cmap=cmap,
        vmin=0,
        vmax=1,
        center=0.5,
        linewidths=0.5,
        figsize=(20, 20),
        cbar_kws={"label": "Log-Volatility Correlation"},
        xticklabels=True,
        yticklabels=True,
    )

    plt.setp(g.ax_heatmap.get_xticklabels(), rotation=90, fontsize=8)
    plt.setp(g.ax_heatmap.get_yticklabels(), rotation=0, fontsize=8)
    g.fig.suptitle("Volatility Risk Clustermap (Systemic Spike Dependencies)", fontsize=20, y=1.02)

    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close()
    logger.info(f"✅ Volatility clustermap saved to: {output_path}")

    return getattr(g, "dendrogram_col", None).linkage if hasattr(g, "dendrogram_col") and g.dendrogram_col else None


def visualize_clusters(returns: pd.DataFrame, output_path: str):
    """
    Generates a hierarchical clustermap of asset correlations.
    """
    if returns.empty:
        return

    logger.info(f"Generating clustermap for {len(returns.columns)} assets...")

    # Filter for non-constant returns
    non_constant = returns.columns[returns.std() > 1e-12].tolist()
    if len(non_constant) < 2:
        logger.warning("Insufficient non-constant assets for clustermap.")
        return

    corr = returns[non_constant].corr()

    # Professional Diverging Palette
    cmap = sns.diverging_palette(230, 20, as_cmap=True)

    # Clustermap with Dendrograms
    g = sns.clustermap(
        corr,
        method="average",
        metric="euclidean",
        cmap=cmap,
        vmin=-1,
        vmax=1,
        center=0,
        linewidths=0.5,
        figsize=(20, 20),
        cbar_kws={"shrink": 0.5},
        xticklabels=True,
        yticklabels=True,
    )

    plt.setp(g.ax_heatmap.get_xticklabels(), rotation=90, fontsize=8)
    plt.setp(g.ax_heatmap.get_yticklabels(), rotation=0, fontsize=8)
    g.fig.suptitle("Hierarchical Correlation Clustermap", fontsize=20, y=1.02)

    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close()
    logger.info(f"✅ Clustermap saved to: {output_path}")


def calculate_concentration_entropy(weights: List[float]) -> float:
    """Calculates the normalized Shannon entropy of a weight distribution."""
    w = np.array(weights)
    w = w[w > 0]
    if len(w) <= 1:
        return 0.0
    p = w / w.sum()
    entropy = -np.sum(p * np.log(p))
    return float(entropy / np.log(len(w)))


def analyze_clusters(clusters_path: str, meta_path: str, returns_path: str, stats_path: str, output_path: str, image_path: str, vol_image_path: str):
    if not os.path.exists(clusters_path) or not os.path.exists(returns_path):
        logger.error(f"Required files missing for cluster analysis: {clusters_path} or {returns_path}")
        return

    with open(clusters_path, "r") as f:
        clusters = cast(Dict[str, List[str]], json.load(f))

    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            raw_meta = json.load(f)
            if isinstance(raw_meta, list):
                meta = {item["symbol"]: item for item in raw_meta}
            else:
                meta = raw_meta

    stats_df = None
    if os.path.exists(stats_path):
        stats_df = pd.read_json(stats_path)

    # Load returns (Parquet or Pickle)
    if returns_path.endswith(".parquet"):
        returns = pd.read_parquet(returns_path)
    else:
        returns = pd.read_pickle(returns_path)

    if not isinstance(returns, pd.DataFrame):
        returns = pd.DataFrame(returns)

    # Force naive index
    try:
        returns.index = pd.to_datetime(returns.index).tz_localize(None)
    except Exception:
        pass

    # Generate Visualizations
    visualize_clusters(returns, image_path)
    vol_linkage = visualize_volatility_clusters(returns, vol_image_path)

    # 1. Start Report Header
    report = []
    report.append(f"# 🧩 Hierarchical Cluster Analysis ({'RAW' if 'raw' in str(output_path) else 'SELECTED'})")
    report.append(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Total Return Clusters:** {len(clusters)}")
    report.append("\n---")

    # 2. Add Visualization Maps
    report.append("## 📈 Correlation Clustermap")
    report.append(f"![Portfolio Clustermap](./{os.path.basename(image_path)})")
    report.append("\n---")

    report.append("## ⚡ Volatility Risk Analysis")
    report.append("Identifies systemic risk units based on volatility co-movement (Log-Vol Correlation).")
    report.append(f"![Volatility Clustermap](./{os.path.basename(vol_image_path)})")

    # Extract Volatility Clusters
    if vol_linkage is not None:
        vol_cluster_ids = sch.fcluster(vol_linkage, t=0.5, criterion="distance")
        vol_clusters: Dict[int, List[str]] = {}
        # Filter symbols used in vol_linkage (non-constant ones)
        vol_symbols = returns.columns[returns.std() > 1e-12].tolist()
        for sym, vc_id in zip(vol_symbols, vol_cluster_ids):
            vc_id_int = int(vc_id)
            if vc_id_int not in vol_clusters:
                vol_clusters[vc_id_int] = []
            vol_clusters[vc_id_int].append(str(sym))

        report.append("\n### 🌪️ Volatility Risk Units")
        report.append("| Unit ID | Size | Assets |")
        report.append("| :--- | :--- | :--- |")
        for vc_id, vc_syms in sorted(vol_clusters.items(), key=lambda x: len(x[1]), reverse=True):
            assets_str = ", ".join([f"`{s}`" for s in vc_syms[:5]])
            if len(vc_syms) > 5:
                assets_str += " ..."
            report.append(f"| {vc_id} | {len(vc_syms)} | {assets_str} |")

    report.append("\n---")

    # 3. Calculate Cluster details
    summary_data = []
    cluster_details = []

    for c_id, symbols in sorted(clusters.items(), key=lambda x: int(x[0])):
        valid_symbols = [s for s in symbols if s in returns.columns]
        if not valid_symbols:
            continue

        sub_rets = cast(pd.DataFrame, returns[valid_symbols])

        # Calculate cluster stats
        non_constant_sub = sub_rets.columns[sub_rets.std() > 1e-12].tolist()
        if len(non_constant_sub) > 1:
            cluster_corr = sub_rets[non_constant_sub].corr()
            corr_values = cluster_corr.values[np.triu_indices_from(cluster_corr.values, k=1)]
            avg_corr = float(np.mean(corr_values))
        else:
            avg_corr = 1.0

        mean_rets = cast(pd.Series, sub_rets.mean(axis=1))
        std_val = float(mean_rets.std())
        cluster_vol = std_val * np.sqrt(252) if not np.isnan(std_val) else 0.0

        cluster_af = 0.0
        cluster_fragility = 0.0
        if stats_df is not None:
            c_stats = stats_df[stats_df["Symbol"].isin(valid_symbols)]
            if not c_stats.empty:
                if "Antifragility_Score" in c_stats.columns:
                    cluster_af = float(c_stats["Antifragility_Score"].mean())
                if "Fragility_Score" in c_stats.columns:
                    cluster_fragility = float(c_stats["Fragility_Score"].mean())

        sectors = [meta.get(s, {}).get("sector", "N/A") for s in valid_symbols]
        sector_series = pd.Series(sectors)
        sector_counts = sector_series.value_counts()
        primary_sector = str(sector_counts.index[0]) if not sector_counts.empty else "N/A"
        sector_homogeneity = float(sector_counts.iloc[0]) / len(valid_symbols) if not sector_counts.empty else 0.0

        markets = list(set(meta.get(s, {}).get("market", "UNKNOWN") for s in valid_symbols))

        # Calculate Cluster Concentration Entropy (if sub-clusters exist or based on raw weights)
        # Note: At this stage we don't have final weights, so we proxy with HRP or Vol-based proxy
        cluster_weights = [1.0 / len(valid_symbols)] * len(valid_symbols)
        entropy = calculate_concentration_entropy(cluster_weights)

        c_detail = []
        c_detail.append(f"\n## 📦 Cluster {c_id}: {primary_sector}")
        c_detail.append(f"- **Size:** {len(valid_symbols)} assets")
        c_detail.append(f"- **Avg Intra-Cluster Correlation:** {avg_corr:.4f}")
        c_detail.append(f"- **Cluster Annualized Vol:** {cluster_vol:.2%}")
        c_detail.append(f"- **Antifragility Score:** {cluster_af:.2f}")
        c_detail.append(f"- **Concentration Entropy:** {entropy:.2f}")
        c_detail.append(f"- **Sector Homogeneity:** {sector_homogeneity:.1%}")
        c_detail.append(f"- **Markets:** {', '.join(markets)}")

        if len(valid_symbols) > 5:
            sub_clusters = perform_subclustering(valid_symbols, returns, threshold=0.2)
            if len(sub_clusters) > 1:
                c_detail.append("\n### 🔍 Nested Sub-Cluster Structure")
                c_detail.append("| Sub-Cluster | Size | Lead Assets | Avg Vol |")
                c_detail.append("| :--- | :--- | :--- | :--- |")
                for sc_id, sc_syms in sorted(sub_clusters.items(), key=lambda x: len(x[1]), reverse=True):
                    sc_rets = returns[sc_syms]
                    sc_mean = cast(pd.Series, sc_rets.mean(axis=1))
                    sc_vol_val = float(sc_mean.std())
                    sc_vol = sc_vol_val * np.sqrt(252) if not np.isnan(sc_vol_val) else 0.0
                    leads = ", ".join([f"`{s}`" for s in sc_syms[:3]])
                    if len(sc_syms) > 3:
                        leads += " ..."
                    c_detail.append(f"| {sc_id} | {len(sc_syms)} | {leads} | {sc_vol:.2%} |")

        c_detail.append("\n### 📋 Members")
        c_detail.append("| Symbol | Description | Sector | Market |")
        c_detail.append("| :--- | :--- | :--- | :--- |")
        for s in valid_symbols:
            s_meta = meta.get(s, {})
            c_detail.append(f"| `{s}` | {s_meta.get('description', 'N/A')} | {s_meta.get('sector', 'N/A')} | {s_meta.get('market', 'UNKNOWN')} |")

        cluster_details.extend(c_detail)
        summary_data.append({"Cluster": c_id, "Sector": primary_sector, "Assets": len(valid_symbols), "Avg_Corr": avg_corr, "Vol": cluster_vol, "Homogeneity": sector_homogeneity})

    summary_table = ["\n## 📊 Clusters Overview", "| Cluster | Primary Sector | Assets | Avg Corr | Vol | Homogeneity |", "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    summary_data.sort(key=lambda x: x["Assets"], reverse=True)
    for s in summary_data:
        summary_table.append(f"| {s['Cluster']} | {s['Sector']} | {s['Assets']} | {s['Avg_Corr']:.3f} | {s['Vol']:.2%} | {s['Homogeneity']:.1%} |")

    full_report = report + summary_table + ["\n---"] + cluster_details
    with open(output_path, "w") as f:
        f.write("\n".join(full_report))
    logger.info(f"✅ Integrated hierarchical cluster analysis report generated at: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["selected", "raw"], default="selected")
    args = parser.parse_args()

    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    # Prioritize run-specific artifacts
    # Phase 173: Prioritize Synthetic Matrix if available
    default_returns = str(run_dir / "data" / "synthetic_returns.parquet")
    if not os.path.exists(default_returns):
        default_returns = str(run_dir / "data" / "returns_matrix.parquet")

    if not os.path.exists(default_returns):
        default_returns = "data/lakehouse/portfolio_returns.pkl"

    default_clusters = str(run_dir / "data" / "portfolio_clusters.json")
    if not os.path.exists(default_clusters):
        default_clusters = "data/lakehouse/portfolio_clusters.json"

    default_meta = str(run_dir / "data" / "portfolio_meta.json")
    if not os.path.exists(default_meta):
        default_meta = "data/lakehouse/portfolio_meta.json"

    c_path = os.getenv("CLUSTERS_FILE" if args.mode == "selected" else "CLUSTERS_RAW", default_clusters)
    m_path = os.getenv("PORTFOLIO_META", default_meta)
    r_path = os.getenv("RETURNS_MATRIX", default_returns)
    s_path = os.getenv("ANTIFRAGILITY_STATS", str(run_dir / "data" / "antifragility_stats.json"))

    out_p = settings.run_reports_dir / "research" / "cluster_analysis.md"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    plot_dir = settings.run_plots_dir / "clustering"
    plot_dir.mkdir(parents=True, exist_ok=True)

    analyze_clusters(
        clusters_path=c_path,
        meta_path=m_path,
        returns_path=r_path,
        stats_path=s_path,
        output_path=str(out_p),
        image_path=str(plot_dir / "portfolio_clustermap.png"),
        vol_image_path=str(plot_dir / "volatility_clustermap.png"),
    )
