from __future__ import annotations

import importlib.util
import logging
from typing import Any, Dict, List, Optional, cast

import pandas as pd

from tradingview_scraper.portfolio_engines.base import EngineRequest, EngineResponse, _effective_cap, _enforce_cap_series
from tradingview_scraper.portfolio_engines.impl.custom import CustomClusteredEngine

logger = logging.getLogger("riskfolio")


class RiskfolioEngine(CustomClusteredEngine):
    @property
    def name(self) -> str:
        return "riskfolio"

    @classmethod
    def is_available(cls) -> bool:
        return bool(importlib.util.find_spec("riskfolio"))

    def optimize(self, *, returns: pd.DataFrame, clusters: Dict[str, List[str]], meta: Optional[Dict[str, Any]] = None, stats: Optional[pd.DataFrame] = None, request: EngineRequest) -> EngineResponse:
        return super().optimize(returns=returns, clusters=clusters, meta=meta, stats=stats, request=request)

    def _optimize_cluster_weights(self, *, universe, request) -> pd.Series:
        import riskfolio as rp

        X = universe.cluster_benchmarks
        n = X.shape[1]

        # CR-590: Strict 25% Cluster Cap Enforcement
        cap_val = min(0.25, float(request.cluster_cap))
        cap = _effective_cap(cap_val, n)

        if n <= 0:
            return pd.Series(dtype=float, index=X.columns)
        if n == 1:
            return pd.Series([1.0], index=X.columns)

        if n < 3:
            return super()._optimize_cluster_weights(universe=universe, request=request)

        try:
            if request.profile == "hrp":
                port = rp.HCPortfolio(returns=X)
                w = port.optimization(model="HRP", codependence="pearson", rm="MV", linkage="ward")
            elif request.profile == "risk_parity" or request.profile == "erc":
                port = rp.Portfolio(returns=X)
                port.assets_stats(method_mu="hist", method_cov="ledoit")
                w = port.rp_optimization(model="Classic", rm="MV", rf=cast(Any, 0.0), b=None)
            elif request.profile == "equal_weight":
                return pd.Series(1.0 / n, index=X.columns)
            else:
                port = rp.Portfolio(returns=X)
                port.assets_stats(method_mu="hist", method_cov="ledoit")

                # CR-290: Market Neutral Constraint
                if request.market_neutral and request.benchmark_returns is not None:
                    logger.info("Riskfolio: Market Neutrality requested, falling back to custom engine")
                    return super()._optimize_cluster_weights(universe=universe, request=request)

                w = port.optimization(
                    model="Classic", rm="MV", obj="Sharpe" if request.profile == "max_sharpe" else "MinRisk", rf=cast(Any, float(request.risk_free_rate)), l=cast(Any, float(request.l2_gamma))
                )

            return _enforce_cap_series((w.iloc[:, 0] if isinstance(w, pd.DataFrame) else pd.Series(w)).reindex(X.columns).fillna(0.0).astype(float), cap)
        except Exception as e:
            logger.error(f"Riskfolio optimization failed: {e}")
            raise
