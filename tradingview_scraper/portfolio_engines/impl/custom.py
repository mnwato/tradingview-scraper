from __future__ import annotations

import dataclasses
import logging
from typing import Any, Dict, List, Optional, cast

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import squareform
from sklearn.covariance import ledoit_wolf

from tradingview_scraper.portfolio_engines.base import BaseRiskEngine, EngineResponse, _effective_cap, _enforce_cap_series, _safe_series
from tradingview_scraper.portfolio_engines.cluster_adapter import ClusteredUniverse, build_clustered_universe
from tradingview_scraper.settings import get_settings

logger = logging.getLogger(__name__)


def _get_recursive_bisection_weights(cov: np.ndarray, sort_ix: List[int]) -> np.ndarray:
    weights = np.ones(len(sort_ix))
    items = [sort_ix]
    while len(items) > 0:
        items = [i[j:k] for i in items for j, k in ((0, len(i) // 2), (len(i) // 2, len(i))) if len(i) > 1]
        for i in range(0, len(items), 2):
            l, r = items[i], items[i + 1]

            # v3.5.5 Hardening: Improved HRP Variance Calculation
            # We use inverse-variance weighted branch variance for more stable bisection
            def get_cluster_var(idx_list):
                if len(idx_list) == 0:
                    return 0.0
                c_cov = cov[idx_list][:, idx_list]
                # Inverse Variance Weights
                vols = np.sqrt(np.diag(c_cov) + 1e-15)
                inv_vars = 1.0 / (vols**2 + 1e-15)
                w_iv = inv_vars / inv_vars.sum()
                return float(w_iv @ c_cov @ w_iv)

            v_l = get_cluster_var(l)
            v_r = get_cluster_var(r)

            alpha = 1 - v_l / (v_l + v_r + 1e-15)
            weights[l] *= alpha
            weights[r] *= 1 - alpha
    return weights


def _weights_df_from_cluster_weights(*, universe: ClusteredUniverse, cluster_weights: pd.Series, meta: Optional[Dict[str, Any]], scale: float = 1.0) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    meta = meta or {}
    for col, c_w in cluster_weights.items():
        c_w_scalar = float(c_w)
        if c_w_scalar <= 0:
            continue
        intra = universe.intra_cluster_weights.get(str(col).replace("Cluster_", ""))
        if intra is None or intra.empty:
            continue
        for sym, sym_w in intra.items():
            sym_w_scalar = float(sym_w)
            w = c_w_scalar * sym_w_scalar * scale
            if w <= 1e-9:
                continue
            m = meta.get(str(sym), {})
            d = str(m.get("direction", "LONG"))
            rows.append(
                {
                    "Symbol": str(sym),
                    "Weight": float(w),
                    "Net_Weight": float(w) * (1.0 if d == "LONG" else -1.0),
                    "Direction": d,
                    "Cluster_ID": str(col).replace("Cluster_", ""),
                    "Cluster_Weight": c_w_scalar * scale,
                    "Intra_Cluster_Weight": sym_w_scalar,
                    "Type": "CORE",
                    "Description": m.get("description", "N/A"),
                    "Sector": m.get("sector", "N/A"),
                    "Market": m.get("market", "UNKNOWN"),
                }
            )
    if not rows:
        return pd.DataFrame(columns=pd.Index(["Symbol", "Weight"]))
    df = pd.DataFrame(rows).sort_values("Weight", ascending=False)
    total = float(df["Weight"].sum())
    if total > 0:
        factor = scale / (total + 1e-12)
        df["Weight"] *= factor
        df["Net_Weight"] *= factor
    return df


def _cov_shrunk(returns: pd.DataFrame, kappa_thresh: float = 15000.0, default_shrinkage: float = 0.01) -> np.ndarray:
    if returns.shape[1] < 2:
        c = returns.cov().values * 252
        return np.asarray(c, dtype=float)
    s_cov, _ = ledoit_wolf(returns.values)
    cov = s_cov * 252
    n, shr = cov.shape[0], default_shrinkage
    while shr <= 0.1:
        vols = np.sqrt(np.diag(cov) + 1e-15)
        corr = cov / np.outer(vols, vols)
        corr_r = corr * (1.0 - shr) + np.eye(n) * shr
        evs = np.linalg.eigvalsh(corr_r)
        k = float(evs.max() / (np.abs(evs).min() + 1e-15))
        if k <= kappa_thresh:
            return np.outer(vols, vols) * corr_r
        shr += 0.01
    return cov + np.eye(n) * 0.1 * np.mean(np.diag(cov))


def _solve_cvxpy(
    *,
    n,
    cap,
    cov,
    mu=None,
    penalties=None,
    profile="min_variance",
    risk_free_rate=0.0,
    prev_weights=None,
    l2_gamma=0.0,
    solver=None,
    solver_options=None,
    betas=None,
    market_neutral=False,
    beta_tolerance=None,
):
    import cvxpy as cp

    if n <= 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])

    w = cp.Variable(n)
    # Constraints: Long only, sum to 1, individual cap
    constraints = [cp.sum(w) == 1.0, w >= 0.0, w <= cap]

    # CR-290: Market Neutral Constraint Hardening (Phase 125)
    if market_neutral and betas is not None:
        tol = beta_tolerance or (0.05 if n >= 15 else 0.15)
        constraints.append(cp.abs(w @ betas) <= tol)

    risk = cp.quad_form(w, cov + np.eye(n) * 1e-6)
    p_t = (w @ penalties) * 0.2 if penalties is not None else 0.0
    l2_val = float(l2_gamma)

    # CR-600: Profile-Specific Numerical Hardening
    if profile == "max_sharpe":
        # Force higher L2 to prevent extreme concentration/outliers in high-alpha chasing
        l2_val = max(l2_val, 0.10)

    l2 = l2_val * cp.sum_squares(w) if l2_val > 0 else 0.0

    t_p = 0.0
    s_obj = get_settings()
    if s_obj.features.feat_turnover_penalty and prev_weights is not None and prev_weights.size == n:
        t_p = cp.norm(w - prev_weights, 1) * 0.001

    if profile == "min_variance":
        obj = cp.Minimize(risk + p_t + t_p + l2)
    elif profile == "risk_parity" or profile == "erc":
        obj = cp.Minimize(0.5 * risk - (1.0 / n) * cp.sum(cp.log(w)) + t_p + l2)
    elif profile == "max_sharpe":
        mu_vec = np.asarray(mu if mu is not None else np.zeros(n), dtype=float).flatten()
        obj = cp.Maximize((mu_vec @ w) - 0.5 * risk - p_t - t_p - l2)
    else:
        obj = cp.Minimize(risk + t_p + l2)

    try:
        prob = cp.Problem(obj, constraints)
        # Use CLARABEL or ECOS for absolute values or risk budgeting
        installed = cp.installed_solvers()
        if profile in ["risk_parity", "erc"] or market_neutral:
            active_s = cp.CLARABEL if "CLARABEL" in installed else (cp.ECOS if "ECOS" in installed else cp.SCS)
        else:
            active_s = cp.OSQP
        if solver:
            active_s = getattr(cp, solver.upper())

        options = solver_options or {}
        prob.solve(solver=active_s, **options)

        if w.value is None or prob.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
            logger.warning(f"Solver failed: status={prob.status}, profile={profile}, neutral={market_neutral}")
            if market_neutral:
                # Recursive fallback to unconstrained or relaxed
                current_tol = beta_tolerance or (0.05 if n >= 15 else 0.15)
                if current_tol < 0.3:
                    logger.info(f"Retrying Market Neutral with relaxed tolerance: {current_tol + 0.1}")
                    return _solve_cvxpy(
                        n=n,
                        cap=cap,
                        cov=cov,
                        mu=mu,
                        penalties=penalties,
                        profile=profile,
                        risk_free_rate=risk_free_rate,
                        prev_weights=prev_weights,
                        l2_gamma=l2_gamma,
                        solver=solver,
                        solver_options=options,
                        betas=betas,
                        market_neutral=True,
                        beta_tolerance=current_tol + 0.1,
                    )
                return _solve_cvxpy(
                    n=n,
                    cap=cap,
                    cov=cov,
                    mu=mu,
                    penalties=penalties,
                    profile=profile,
                    risk_free_rate=risk_free_rate,
                    prev_weights=prev_weights,
                    l2_gamma=l2_gamma,
                    solver=solver,
                    solver_options=options,
                    betas=betas,
                    market_neutral=False,
                    beta_tolerance=None,
                )
            return np.array([1.0 / n] * n)

        return np.array(w.value).flatten()
    except Exception as e:
        logger.error(f"CVXPY Internal Error: {e}")
        return np.array([1.0 / n] * n)


def _cluster_penalties(u):
    return np.array([float(u.cluster_stats.get(str(c).replace("Cluster_", ""), {}).get("fragility", 1.0)) for c in u.cluster_benchmarks.columns])


class CustomClusteredEngine(BaseRiskEngine):
    @property
    def name(self) -> str:
        return "custom"

    @classmethod
    def is_available(cls) -> bool:
        return True

    def optimize(self, *, returns, clusters, meta=None, stats=None, request):
        if request.profile == "equal_weight":
            targets = list(returns.columns)
            if not targets:
                return EngineResponse(self.name, request, pd.DataFrame(), {"backend": "custom_empty"}, ["empty returns"])

            # CR-590: Capped Equal Weight
            n_assets = len(targets)
            w_raw = 1.0 / n_assets
            w_capped = min(0.25, w_raw)
            # If capped, we have leftover. Standard is to redistribute or just use w_raw if N is small.
            # But the requirement is 25% cap.
            w = w_capped

            rows = [
                {
                    "Symbol": str(s),
                    "Weight": w,
                    "Net_Weight": w * (1.0 if (meta or {}).get(str(s), {}).get("direction", "LONG") == "LONG" else -1.0),
                    "Direction": (meta or {}).get(str(s), {}).get("direction", "LONG"),
                    "Cluster_ID": "ASSET_EW",
                    "Description": (meta or {}).get(str(s), {}).get("description", "N/A"),
                }
                for s in targets
            ]
            return EngineResponse(self.name, request, pd.DataFrame(rows), {"backend": "custom_asset_ew"}, [])

        u = build_clustered_universe(returns=returns, clusters=clusters, meta=meta, stats=stats)
        if u.cluster_benchmarks.empty:
            return EngineResponse(self.name, request, pd.DataFrame(columns=pd.Index(["Symbol", "Weight"])), {"backend": "custom"}, ["empty universe"])

        if request.profile == "barbell":
            w_df, m_out, warn = self._barbell(universe=u, meta=meta, stats=stats, request=request)
            return EngineResponse(self.name, request, w_df, m_out, warn)

        c_w = self._optimize_cluster_weights(universe=u, request=request)
        return EngineResponse(self.name, request, _weights_df_from_cluster_weights(universe=u, cluster_weights=c_w, meta=meta), {"backend": "custom"}, [])

    def _optimize_cluster_weights(self, *, universe, request) -> pd.Series:
        X = universe.cluster_benchmarks
        n = X.shape[1]
        if n <= 0:
            return pd.Series(dtype=float, index=X.columns)
        if n == 1:
            return pd.Series([1.0], index=X.columns)

        # CR-FIX: HRP Robustness - Drop Zero Variance Columns
        # Identify valid columns (non-zero variance)
        valid_cols = [c for c in X.columns if X[c].std() > 1e-9]
        dropped_cols = [c for c in X.columns if c not in valid_cols]

        if dropped_cols:
            logger.warning(f"Dropping {len(dropped_cols)} zero-variance clusters from optimization: {dropped_cols}")
            X_clean = X[valid_cols]
        else:
            X_clean = X

        n_clean = X_clean.shape[1]
        if n_clean <= 0:
            return pd.Series(0.0, index=X.columns)

        if n_clean == 1:
            w_clean = pd.Series([1.0], index=X_clean.columns)
            return w_clean.reindex(X.columns, fill_value=0.0)

        # CR-590: Strict 25% Cluster Cap Enforcement
        cap_val = min(0.25, float(request.cluster_cap))
        cap = _effective_cap(cap_val, n_clean)

        # Calculate covariance on clean data
        cov = _cov_shrunk(X_clean, kappa_thresh=request.kappa_shrinkage_threshold, default_shrinkage=request.default_shrinkage_intensity)

        if request.profile == "hrp":
            link = sch.linkage(squareform(np.sqrt(0.5 * (1 - X_clean.corr().values.clip(-1, 1))), checks=False), method="ward")
            # Ensure sort_ix is a list of ints
            sort_ix = cast(List[int], sch.leaves_list(link).tolist())
            w_np = _get_recursive_bisection_weights(cov, sort_ix)
            w_series = _enforce_cap_series(pd.Series(w_np, index=X_clean.columns), cap)
            return w_series.reindex(X.columns, fill_value=0.0)

        l2 = {"EXPANSION": 0.05, "INFLATIONARY_TREND": 0.10, "STAGNATION": 0.10, "CRISIS": 0.20}.get(request.market_environment, 0.05)
        p_w = None
        if request.prev_weights is not None and not request.prev_weights.empty:
            p_w = np.zeros(n_clean)
            for sym_key, weight in request.prev_weights.items():
                c_id = universe.symbol_to_cluster.get(str(sym_key))
                if c_id and f"Cluster_{c_id}" in X_clean.columns:
                    p_w[X_clean.columns.get_loc(f"Cluster_{c_id}")] += float(weight)
            if p_w.sum() > 0:
                p_w /= p_w.sum()

        betas = None
        s_obj = get_settings()
        is_neutral = request.market_neutral and s_obj.features.feat_market_neutral

        if is_neutral and request.benchmark_returns is not None:
            from tradingview_scraper.utils.synthesis import calculate_beta

            betas = np.array([calculate_beta(X_clean[col], request.benchmark_returns) for col in X_clean.columns])

        mu = np.asarray(X_clean.mean(), dtype=float).flatten() * 252

        # Helper to align penalties with cleaned columns
        def _get_clean_penalties(u, clean_cols):
            # _cluster_penalties returns array aligned with u.cluster_benchmarks.columns
            # We map back to indices
            all_pens = _cluster_penalties(u)
            # Map column name to index in original X
            original_cols = u.cluster_benchmarks.columns
            indices = [original_cols.get_loc(c) for c in clean_cols]
            return all_pens[indices]

        w = _solve_cvxpy(
            n=n_clean,
            cap=cap,
            cov=cov,
            mu=mu,
            penalties=_get_clean_penalties(universe, X_clean.columns),
            profile=request.profile,
            risk_free_rate=float(request.risk_free_rate),
            prev_weights=p_w,
            l2_gamma=l2,
            betas=betas,
            market_neutral=is_neutral,
            beta_tolerance=None,
        )

        # Re-index result to match original columns
        w_series = _safe_series(w, X_clean.columns)
        return w_series.reindex(X.columns, fill_value=0.0)

    def _barbell(self, *, universe, meta=None, stats=None, request):
        if stats is None or stats.empty:
            return pd.DataFrame(columns=pd.Index(["Symbol", "Weight"])), {"backend": "custom"}, ["missing stats"]
        stats_l = stats.copy()
        if "Symbol" not in stats_l.columns:
            stats_l["Symbol"] = stats_l.index
        if "Antifragility_Score" not in stats_l.columns:
            return pd.DataFrame(columns=pd.Index(["Symbol", "Weight"])), {"backend": "custom"}, ["Antifragility_Score missing"]

        # CR-271: Map physical symbols in stats to strategy IDs in universe (3-Pillar Synthesis)
        s2c = universe.symbol_to_cluster
        sym_to_strat = {}
        for strat_id in universe.returns.columns:
            for phys in stats_l["Symbol"].tolist():
                if strat_id.startswith(f"{phys}_"):
                    sym_to_strat[str(phys)] = str(strat_id)

        # Replace physical symbols with strategy IDs to ensure 'flatten_weights' works downstream
        stats_l["Symbol"] = stats_l["Symbol"].apply(lambda s: sym_to_strat.get(str(s), s))

        def get_cluster(sym):
            return s2c.get(str(sym))

        stats_l["Cluster_ID"] = stats_l["Symbol"].apply(get_cluster)
        stats_l = stats_l.dropna(subset=["Cluster_ID"])
        if stats_l.empty:
            return pd.DataFrame(columns=pd.Index(["Symbol", "Weight"])), {"backend": "custom"}, ["no mapping"]

        ranked = stats_l.sort_values("Antifragility_Score", ascending=False).groupby("Cluster_ID").first().sort_values("Antifragility_Score", ascending=False)
        m_a_c = min(min(int(request.max_aggressor_clusters), max(1, len(ranked) // 2)), len(ranked) - 1)

        if m_a_c <= 0:
            return (
                _weights_df_from_cluster_weights(universe=universe, cluster_weights=self._optimize_cluster_weights(universe=universe, request=dataclasses.replace(request, profile="hrp")), meta=meta),
                {"backend": "custom"},
                ["barbell fallback"],
            )

        agg_syms = [str(s) for s in ranked.head(m_a_c)["Symbol"].tolist()]
        agg_total = {"QUIET": 0.15, "NORMAL": 0.10, "TURBULENT": 0.05, "CRISIS": 0.03}.get(request.regime, float(request.aggressor_weight))
        agg_per = max(0.0, min(0.95, agg_total)) / len(agg_syms)
        excluded = [s for c_id in ranked.head(m_a_c).index for s in universe.clusters.get(str(c_id), [])]
        core_syms = [s for s in universe.returns.columns if s not in excluded]
        if not core_syms:
            return pd.DataFrame(columns=pd.Index(["Symbol", "Weight"])), {"backend": "custom"}, ["no core"]

        c_prof = "hrp" if len(core_syms) >= 10 else "equal_weight"
        c_u = build_clustered_universe(
            returns=universe.returns,
            clusters={c_id: [s for s in syms if s in core_syms] for c_id, syms in universe.clusters.items() if str(c_id) not in ranked.head(m_a_c).index},
            meta=meta,
            stats=stats,
        )
        c_w_df = _weights_df_from_cluster_weights(
            universe=c_u, cluster_weights=self._optimize_cluster_weights(universe=c_u, request=dataclasses.replace(request, profile=c_prof)), meta=meta, scale=(1.0 - agg_total)
        )

        agg_rows = [
            {
                "Symbol": s,
                "Weight": agg_per,
                "Net_Weight": agg_per * (1.0 if (meta or {}).get(s, {}).get("direction", "LONG") == "LONG" else -1.0),
                "Direction": (meta or {}).get(s, {}).get("direction", "LONG"),
                "Cluster_ID": str(universe.symbol_to_cluster.get(s)),
                "Type": "AGGRESSOR",
                "Description": (meta or {}).get(s, {}).get("description", "N/A"),
                "Sector": (meta or {}).get(s, {}).get("sector", "N/A"),
                "Market": (meta or {}).get(s, {}).get("market", "UNKNOWN"),
            }
            for s in agg_syms
        ]
        combined = pd.concat([pd.DataFrame(agg_rows), c_w_df], ignore_index=True)
        combined["Weight"] /= float(combined["Weight"].sum()) + 1e-12
        return combined, {"backend": "custom", "aggressor_clusters": ranked.head(m_a_c).index.tolist()}, []
