# pyright: reportGeneralTypeIssues=false
import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import squareform

from tradingview_scraper.regime import MarketRegimeDetector
from tradingview_scraper.settings import get_settings


def winsorize(df: pd.DataFrame, alpha: float) -> pd.DataFrame:
    if alpha <= 0:
        return df
    lower = df.quantile(alpha, axis=0)
    upper = df.quantile(1 - alpha, axis=0)
    return cast(pd.DataFrame, df.clip(lower=lower, upper=upper, axis=1))


def get_robust_correlation(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates a robust correlation matrix using intersection of active trading days
    to avoid dilution from padding (e.g. TradFi weekends vs Crypto 24/7).
    """
    symbols = returns.columns
    n = len(symbols)
    corr_matrix = np.eye(n)

    # Process each pair individually to ensure intersection correlation
    for i in range(n):
        for j in range(i + 1, n):
            s1 = str(symbols[i])
            s2 = str(symbols[j])

            # Extract pair and drop zeros/NaNs
            v1 = cast(np.ndarray, returns[s1].values)
            v2 = cast(np.ndarray, returns[s2].values)

            mask = np.logical_and(np.logical_and(v1 != 0, v2 != 0), np.logical_and(~np.isnan(v1), ~np.isnan(v2)))

            v1_clean = v1[mask]
            v2_clean = v2[mask]

            if len(v1_clean) < 20:
                c = 0.0
            else:
                c = float(np.corrcoef(v1_clean, v2_clean)[0, 1])
                if np.isnan(c):
                    c = 0.0

            corr_matrix[i, j] = c
            corr_matrix[j, i] = c

    return pd.DataFrame(corr_matrix, index=symbols, columns=symbols)


def load_returns(path: Path, min_col_frac: float, candidates_path: Optional[Path] = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Returns file not found: {path}")

    if str(path).endswith(".parquet"):
        rets_raw = pd.read_parquet(path)
    else:
        with open(path, "rb") as f:
            rets_raw = pd.read_pickle(f)

    if not isinstance(rets_raw, pd.DataFrame):
        rets = pd.DataFrame(rets_raw)
    else:
        rets = rets_raw

    # Filter by candidates if provided (Sync with Natural Selection)
    if candidates_path and candidates_path.exists():
        with open(candidates_path, "r") as f:
            candidates = json.load(f)
        # CR-823: Atom-Aware Filtering
        selected_ids = []
        for c in candidates:
            # Try full atom_id first (Asset_Logic_Direction)
            sym = c["symbol"]
            logic = c.get("logic") or "trend"
            direction = c.get("direction") or "LONG"
            atom_id = f"{sym}_{logic}_{direction}"
            selected_ids.append(atom_id)

        common = [s for s in selected_ids if s in rets.columns]
        # Fallback to pure symbols if no atoms match (Legacy support)
        if not common:
            pure_syms = [c["symbol"] for c in candidates]
            common = [s for s in pure_syms if s in rets.columns]

        rets = rets[common]

    # Drop columns with too many NaNs
    min_count = int(min_col_frac * len(rets))
    # CRITICAL: Do not drop rows (Inner Join) here, as it will truncate the matrix
    # to the shortest asset's listing day, dropping almost all assets in high-growth portfolios.
    # Clustering will use Robust (Pairwise) Correlation instead.
    if min_count > 0:
        counts = rets.count()
        rets = rets.loc[:, counts >= min_count]

    # Fill remaining NaNs with 0 to allow standard matrix operations
    # while preserving the temporal variance profile of each asset.
    rets = rets.fillna(0.0)

    # Drop zero-variance cols
    var = rets.var()
    rets = rets.loc[:, var > 0]
    return rets


def rolling_avg_corr(rets: pd.DataFrame, window: int) -> pd.Series:
    if len(rets) < window:
        return pd.Series(dtype=float)
    # This remains a simple average for regime detection proxy
    roll = rets.rolling(window).corr()
    avg = roll.groupby(level=0).mean().mean(axis=1)
    return pd.Series(avg, dtype=float)


def top_corr_pairs(corr: pd.DataFrame, cap: float, limit: int) -> List[Tuple[str, str, float]]:
    symbols = list(corr.columns)
    corr_abs = corr.abs().to_numpy()
    out: List[Tuple[str, str, float]] = []
    seen = set()
    for i in range(len(symbols)):
        for j in range(i):
            v = float(corr_abs[i, j])
            if v < cap:
                continue
            key = tuple(sorted((str(symbols[i]), str(symbols[j]))))
            if key in seen:
                continue
            seen.add(key)
            out.append((str(symbols[i]), str(symbols[j]), v))
    out.sort(key=lambda x: x[2], reverse=True)
    return out[:limit]


def hrp_weights(rets: pd.DataFrame, linkage_method: str) -> pd.Series:
    if rets.shape[1] == 0:
        return pd.Series(dtype=float)

    cov = rets.cov().to_numpy()
    corr_df = get_robust_correlation(rets)
    corr = corr_df.values

    dist = np.sqrt(0.5 * (np.ones_like(corr) - corr))
    dist = (dist + dist.T) / 2
    np.fill_diagonal(dist, 0)

    condensed = squareform(dist, checks=False)
    link = sch.linkage(condensed, method=linkage_method)
    order = sch.leaves_list(link)
    ordered_cols = rets.columns[order]

    def get_ivp(cov_sub: np.ndarray) -> np.ndarray:
        inv_diag = 1 / (np.diag(cov_sub) + 1e-9)
        return inv_diag / inv_diag.sum()

    def cluster_var(cov_mat: np.ndarray, idxs: List[int]) -> float:
        sub = cov_mat[np.ix_(idxs, idxs)]
        ivp = get_ivp(sub)
        return float(ivp.T @ sub @ ivp)

    weights = pd.Series(1.0, index=ordered_cols)
    clusters: List[List[int]] = [list(range(len(ordered_cols)))]
    while clusters:
        cluster = clusters.pop(0)
        if len(cluster) <= 1:
            continue
        mid = len(cluster) // 2
        left, right = cluster[:mid], cluster[mid:]
        var_left = cluster_var(cov, left)
        var_right = cluster_var(cov, right)
        alloc_left = var_right / (var_left + var_right + 1e-9)
        alloc_right = var_left / (var_left + var_right + 1e-9)
        weights.iloc[left] *= alloc_left
        weights.iloc[right] *= alloc_right
        clusters.extend([left, right])

    return weights / weights.sum()


def main():
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    default_returns = str(run_dir / "data" / "returns_matrix.parquet")
    if not os.path.exists(default_returns):
        default_returns = "data/lakehouse/portfolio_returns.pkl"

    default_candidates = str(run_dir / "data" / "portfolio_candidates.json")
    if not os.path.exists(default_candidates):
        default_candidates = "data/lakehouse/portfolio_candidates.json"

    default_clusters = str(run_dir / "data" / "portfolio_clusters.json")

    parser = argparse.ArgumentParser(description="Generate correlation/HRP report")
    parser.add_argument("--returns", default=os.getenv("RETURNS_MATRIX", default_returns))
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--pair-cap", type=float, default=0.85)
    parser.add_argument("--pair-limit", type=int, default=20)
    parser.add_argument("--winsor-alpha", type=float, default=0.0)
    parser.add_argument("--min-col-frac", type=float, default=settings.features.min_col_frac)
    parser.add_argument("--windows", default="20,60,180")
    parser.add_argument("--regime-z", type=float, default=1.5)
    parser.add_argument("--linkage", default="ward")
    parser.add_argument("--hrp", action="store_true", help="Emit HRP weights")
    parser.add_argument("--max-clusters", type=int, default=settings.max_clusters if hasattr(settings, "max_clusters") else 25, help="Target maximum number of clusters")
    parser.add_argument("--out-clusters", default=os.getenv("CLUSTERS_FILE", default_clusters), help="Path to save cluster JSON")
    parser.add_argument("--candidates", default=os.getenv("CANDIDATES_SELECTED", default_candidates), help="Path to selected candidates")
    args = parser.parse_args()

    if args.out_dir:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = get_settings().prepare_summaries_run_dir()

    rets = load_returns(Path(args.returns), args.min_col_frac, Path(args.candidates))
    if args.winsor_alpha > 0:
        rets = winsorize(rets, args.winsor_alpha)

    windows = [int(w) for w in args.windows.split(",") if w.strip()]
    avg_corr_series = {w: rolling_avg_corr(rets, w) for w in windows}

    # Multi-Factor Regime Detection
    detector = MarketRegimeDetector()
    regime_name, regime_score, quadrant = detector.detect_regime(rets)
    print(f"Regime Detected: {regime_name} (Score: {regime_score:.2f}) | Quadrant: {quadrant}")

    # Adaptive Clustering Threshold
    dist_threshold = 0.4
    if regime_name == "CRISIS":
        dist_threshold = 0.3
    elif regime_name == "QUIET":
        dist_threshold = 0.5

    # Robust Correlation for reporting
    shrunk_corr = get_robust_correlation(rets)
    top_pairs = top_corr_pairs(shrunk_corr, args.pair_cap, args.pair_limit)

    report: Dict[str, Any] = {
        "params": {
            "pair_cap": args.pair_cap,
            "pair_limit": args.pair_limit,
            "winsor_alpha": args.winsor_alpha,
            "min_col_frac": args.min_col_frac,
            "windows": windows,
            "regime_z": args.regime_z,
            "linkage": args.linkage,
            "hrp": args.hrp,
            "dist_threshold": dist_threshold,
        },
        "n_assets": rets.shape[1],
        "avg_corr": {w: float(avg_corr_series[w].iloc[-1]) if not avg_corr_series[w].empty else None for w in windows},
        "regime": {"name": regime_name, "score": regime_score},
        "top_pairs": top_pairs,
    }

    if args.hrp:
        clusters: Dict[int, List[str]] = {}

        if rets.shape[1] > 1:
            w_hrp = hrp_weights(rets, args.linkage)
            report["hrp_weights"] = w_hrp.to_dict()

            # Extract clusters using Robust Correlation
            corr = shrunk_corr.values
            dist = np.sqrt(0.5 * (1 - np.clip(corr, -1, 1)))
            dist = (dist + dist.T) / 2
            np.fill_diagonal(dist, 0)
            condensed = squareform(dist, checks=False)
            link = sch.linkage(condensed, method=args.linkage)

            # Adaptive Clustering Threshold or Max Clusters
            # If max-clusters is set, use it as the primary criterion
            cluster_assignments = sch.fcluster(link, t=args.max_clusters, criterion="maxclust")

            for sym, cluster_id in zip(rets.columns, cluster_assignments):
                c_id = int(cluster_id)
                if c_id not in clusters:
                    clusters[c_id] = []
                clusters[c_id].append(str(sym))
        elif rets.shape[1] == 1:
            # Single asset case
            clusters[1] = [str(rets.columns[0])]
            report["hrp_weights"] = {str(rets.columns[0]): 1.0}
        else:
            # No assets
            clusters[1] = []

        report["clusters"] = clusters

        cluster_path = Path(args.out_clusters)
        with open(cluster_path, "w") as f_out:
            json.dump(clusters, f_out, indent=2)
        print(f"Saved {len(clusters)} clusters to {cluster_path}")

    settings = get_settings()
    settings.prepare_summaries_run_dir()

    json_path = settings.run_data_dir / "metadata" / "correlations.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2))

    # Markdown summary
    lines = ["# Correlation Report", "", f"Assets: {rets.shape[1]}", ""]
    lines.append(f"## Multi-Factor Regime: {regime_name} (Score: {regime_score:.2f})")
    lines.append(f"Applied Clustering Threshold: t={dist_threshold}")
    lines.append("")
    lines.append("## Rolling Correlations (avg corr, z >= %.2f)" % args.regime_z)
    for w in windows:
        val = report["avg_corr"].get(w)
        lines.append(f"- Window {w}d: {val}")
    lines.append("")
    lines.append("## Top pairs (|corr| >= %.2f)" % args.pair_cap)
    for a, b, v in top_pairs:
        lines.append(f"- {a} / {b}: {v:.3f}")
    if args.hrp and rets.shape[1] > 1:
        lines.append("")
        lines.append("## HRP Weights")
        hrp_dict = report.get("hrp_weights")
        if isinstance(hrp_dict, dict):
            for sym, w in sorted(hrp_dict.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- {sym}: {w:.4f}")

    md_path = settings.run_reports_dir / "research" / "correlations.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
