from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, cast

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClusteredUniverse:
    returns: pd.DataFrame
    clusters: Dict[str, List[str]]
    cluster_benchmarks: pd.DataFrame
    intra_cluster_weights: Dict[str, pd.Series]
    cluster_stats: Dict[str, Dict[str, float]]
    symbol_to_cluster: Dict[str, str]


def build_clustered_universe(*, returns: pd.DataFrame, clusters: Dict[str, Any], meta: Optional[Dict[str, Any]] = None, stats: Optional[pd.DataFrame] = None) -> ClusteredUniverse:
    meta = meta or {}

    cluster_map: Dict[str, List[str]] = {}
    for cid, val in clusters.items():
        if isinstance(val, dict) and "selected" in val:
            cluster_map[str(cid)] = val["selected"]
        elif isinstance(val, list):
            cluster_map[str(cid)] = val
        else:
            logger.warning(f"Unsupported cluster format for cid {cid}: {type(val)}")

    all_syms = [s for syms in cluster_map.values() for s in syms]
    avail = [s for s in all_syms if s in returns.columns]

    if not avail:
        logger.warning("build_clustered_universe: No available symbols in returns.")
        return ClusteredUniverse(pd.DataFrame(), {}, pd.DataFrame(), {}, {}, {})

    # 70% Coverage Gate
    thresh = len(returns) * 0.7
    valid_cols = [s for s in avail if returns[s].count() >= thresh]
    if not valid_cols:
        counts = returns[avail].count()
        if isinstance(counts, pd.Series) and not counts.empty:
            max_c = float(counts.max())
            valid_cols = [s for s in avail if float(counts[s]) >= max_c * 0.8]

    if not valid_cols:
        return ClusteredUniverse(pd.DataFrame(), {}, pd.DataFrame(), {}, {}, {})
    aligned = cast(pd.DataFrame, returns[valid_cols].fillna(0.0))
    cb, icw, cs, s2c = pd.DataFrame(index=aligned.index), {}, {}, {}

    for cid, syms in cluster_map.items():
        v_syms = [s for s in syms if s in aligned.columns]
        if not v_syms:
            continue
        for s in v_syms:
            s2c[str(s)] = str(cid)
        sub = aligned[v_syms]
        vols = pd.Series({s: float(sub[s].std() * np.sqrt(252)) for s in v_syms})
        vols = vols.replace(0, 1e-6).fillna(1e-6)
        inv_vars = 1.0 / (vols**2 + 1e-12)
        w_intra = inv_vars / inv_vars.sum()
        bench = (sub * w_intra).sum(axis=1)
        if len(bench.dropna()) > 1 and (bench.std() > 1e-12 or len(v_syms) == 1):
            cb[f"Cluster_{cid}"] = bench
            icw[str(cid)] = w_intra
            from tradingview_scraper.regime import MarketRegimeDetector

            h = MarketRegimeDetector()._hurst_exponent(bench.values)
            cs[str(cid)] = {"fragility": 0.5, "cvar": -0.05, "hurst": h}

    return ClusteredUniverse(aligned, cluster_map, cb, icw, cs, s2c)
