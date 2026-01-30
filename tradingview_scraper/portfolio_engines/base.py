from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import pandas as pd

# Updated ProfileName: Removed 'market_neutral' as it's now a constraint
ProfileName = Literal["min_variance", "hrp", "max_sharpe", "barbell", "equal_weight", "benchmark", "market", "adaptive", "risk_parity", "erc", "market_neutral"]


class EngineUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class EngineRequest:
    profile: ProfileName
    engine: str = "custom"
    cluster_cap: float = 0.25
    risk_free_rate: float = 0.0
    l2_gamma: float = 0.05
    aggressor_weight: float = 0.10
    max_aggressor_clusters: int = 5
    regime: str = "NORMAL"
    market_environment: str = "NORMAL"
    bayesian_params: Dict[str, Any] = field(default_factory=dict)
    prev_weights: Optional[pd.Series] = None
    kappa_shrinkage_threshold: float = 15000.0
    default_shrinkage_intensity: float = 0.01
    adaptive_fallback_profile: str = "erc"

    # CR-290: Market Neutrality as a Constraint
    market_neutral: bool = False
    target_beta: float = 0.0
    # Optional benchmark returns for beta calculation
    benchmark_returns: Optional[pd.Series] = None


@dataclass(frozen=True)
class EngineResponse:
    engine: str
    request: EngineRequest
    weights: pd.DataFrame
    meta: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class BaseRiskEngine(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        return True

    @abstractmethod
    def optimize(self, *, returns: pd.DataFrame, clusters: Dict[str, List[str]], meta: Optional[Dict[str, Any]] = None, stats: Optional[pd.DataFrame] = None, request: EngineRequest) -> EngineResponse:
        pass


def _effective_cap(cluster_cap: float, n: int) -> float:
    if n <= 0:
        return 1.0
    return float(max(cluster_cap, 1.0 / n))


def _safe_series(values: np.ndarray, index: pd.Index) -> pd.Series:
    if len(index) != len(values):
        raise ValueError("weights and index size mismatch")
    if len(index) == 0:
        return pd.Series(dtype=float, index=index)
    res_s = pd.Series(values, index=index).fillna(0.0)
    total_sum = float(res_s.sum())
    if total_sum <= 0:
        return pd.Series(1.0 / len(index), index=index) if len(index) > 0 else pd.Series(dtype=float, index=index)
    return res_s / total_sum


def _project_capped_simplex(values: np.ndarray, cap: float) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    n = int(arr.size)
    if n <= 0:
        return arr
    if n == 1:
        return np.array([1.0])
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    cap_val = _effective_cap(cap, n)
    lo, hi = float(arr.min() - cap_val), float(arr.max())
    for _ in range(60):
        mid = (lo + hi) / 2.0
        w = np.minimum(cap_val, np.maximum(0.0, arr - mid))
        if float(w.sum()) > 1.0:
            lo = mid
        else:
            hi = mid
    w = np.minimum(cap_val, np.maximum(0.0, arr - hi))
    s_val = float(w.sum())
    if s_val <= 0:
        return np.array([1.0 / n] * n)
    res = 1.0 - s_val
    if abs(res) > 1e-9:
        if res > 0:
            w[int(np.argmax(cap_val - w))] = min(cap_val, w[int(np.argmax(cap_val - w))] + res)
        else:
            w[int(np.argmax(w))] = max(0.0, w[int(np.argmax(w))] + res)
    return w


def _enforce_cap_series(weights: pd.Series, cap: float) -> pd.Series:
    return pd.Series(_project_capped_simplex(np.asarray(weights, dtype=float), cap), index=weights.index)


class MarketBaselineEngine(BaseRiskEngine):
    @property
    def name(self) -> str:
        return "market"

    @classmethod
    def is_available(cls) -> bool:
        return True

    def optimize(self, *, returns: pd.DataFrame, clusters: Dict[str, List[str]], meta: Optional[Dict[str, Any]] = None, stats: Optional[pd.DataFrame] = None, request: EngineRequest) -> EngineResponse:
        targets = list(returns.columns)
        if request.profile == "market":
            from tradingview_scraper.settings import get_settings

            s = get_settings()
            bench_targets = [sym for sym in s.benchmark_symbols if sym in returns.columns]
            if bench_targets:
                targets = bench_targets

        if not targets:
            return EngineResponse(self.name, request, pd.DataFrame(), {"backend": "market_empty"}, ["no targets found"])

        w = 1.0 / len(targets)
        rows = [
            {
                "Symbol": str(s),
                "Weight": w,
                "Net_Weight": w * (1.0 if (meta or {}).get(str(s), {}).get("direction", "LONG") == "LONG" else -1.0),
                "Direction": (meta or {}).get(str(s), {}).get("direction", "LONG"),
                "Cluster_ID": "BASELINE",
                "Description": (meta or {}).get(str(s), {}).get("description", "N/A"),
            }
            for s in targets
        ]
        return EngineResponse(self.name, request, pd.DataFrame(rows), {"backend": "baseline_ew"}, [])
