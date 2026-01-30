from typing import Tuple

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import squareform

from tradingview_scraper.settings import get_settings


def get_robust_correlation(returns: pd.DataFrame, shrinkage: float = 0.01) -> pd.DataFrame:
    """
    Computes a shrinkage-adjusted correlation matrix for numerical stability.
    """
    if returns.empty:
        return pd.DataFrame()
    corr = returns.replace(0, np.nan).corr(min_periods=20).fillna(0.0)
    if not corr.empty:
        n = corr.shape[0]
        # Ridge adjustment
        corr = corr * (1.0 - shrinkage) + np.eye(n) * shrinkage
    return corr


def get_hierarchical_clusters(returns: pd.DataFrame, threshold: float = 0.5, max_clusters: int = 25) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes averaged distance matrix and performs Ward Linkage clustering.
    Returns (cluster_ids, linkage_matrix).
    """
    if returns.empty:
        return np.array([]), np.array([])

    settings = get_settings()
    lookbacks = settings.cluster_lookbacks
    available_len = len(returns)
    valid_lookbacks = [l for l in lookbacks if l <= available_len] or [available_len]

    dist_matrices = []
    for l in valid_lookbacks:
        corr = get_robust_correlation(returns.tail(l), shrinkage=settings.features.default_shrinkage_intensity)
        if not corr.empty:
            dist_matrices.append(np.sqrt(0.5 * (1 - corr.values.clip(-1, 1))))

    if not dist_matrices:
        return np.array([1] * len(returns.columns)), np.array([])

    avg_dist = np.mean(dist_matrices, axis=0)
    avg_dist = (avg_dist + avg_dist.T) / 2
    np.fill_diagonal(avg_dist, 0)

    if len(returns.columns) < 2:
        return np.array([1]), np.array([])

    link = sch.linkage(squareform(avg_dist, checks=False), method="ward")

    # CR-650: Hard-Bounded Cluster Resolution
    # We prioritize the distance threshold but enforce max_clusters as a hard ceiling
    cluster_ids = sch.fcluster(link, t=threshold, criterion="distance")
    n_generated = len(np.unique(cluster_ids))

    if n_generated > max_clusters:
        # Fallback to maxclust to ensure factor aggregation
        cluster_ids = sch.fcluster(link, t=max_clusters, criterion="maxclust")

    return cluster_ids, link
