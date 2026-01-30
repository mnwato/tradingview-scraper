from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, cast

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Institutional Gates
# Lowered significantly to allow metrics for short walk-forward windows (e.g. 20d)
MIN_OBSERVATIONS = 2
# Epsilon jitter to prevent empty slices in quantile-based risk metrics (returns < var)
EPSILON_JITTER = 1e-12


def _apply_jitter(rets: pd.Series) -> pd.Series:
    """Adds negligible unique noise to break ties in flat distributions."""
    if rets.empty:
        return rets
    return rets + np.linspace(0, EPSILON_JITTER, len(rets))


def _get_annualization_factor(rets: pd.Series) -> int:
    """
    Detects frequency and returns 252 for 5-day week or 365 for 7-day week.
    Standardizes on 365 for Crypto sleeves.
    """
    from tradingview_scraper.settings import get_settings

    settings = get_settings()

    # If explicitly set in environment or manifest (Future)
    # For now, we detect 24/7 markets
    try:
        idx = rets.index
        if not isinstance(idx, pd.DatetimeIndex):
            idx = pd.to_datetime(idx)

        # Check for weekends in the data
        days = getattr(idx, "dayofweek")
        if any(d in [5, 6] for d in days):
            return 365

        # Check if the asset is crypto based on naming convention
        name_str = str(getattr(rets, "name", "") or "").upper()
        if "USDT" in name_str or "USDC" in name_str:
            return 365

    except Exception:
        pass

    # Global default from settings if available (e.g. backtest_annualization_factor)
    return 252


def calculate_max_drawdown(series: pd.Series | np.ndarray) -> float:
    """Calculates Max Drawdown for a return series."""
    if isinstance(series, np.ndarray):
        series = pd.Series(series)

    cum_ret = (1 + series).cumprod()
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / (running_max + 1e-12)
    return float(drawdown.min())


def calculate_performance_metrics(daily_returns: pd.Series, periods: Optional[int] = None) -> Dict[str, Any]:
    """
    Computes a standardized suite of performance metrics using QuantStats.
    Adds robustness against anomalous data, extreme volatility, and bankruptcy.
    """
    empty_res = {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "realized_vol": 0.0,
        "annualized_vol": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
        "var_95": None,
        "cvar_95": None,
        "sortino": 0.0,
        "calmar": 0.0,
        "omega": 0.0,
    }

    if daily_returns.empty:
        return empty_res

    # CR-FIX: Data Hygiene - Drop extreme outliers that would corrupt CAGR
    # Returns > 1000% in a single day are almost certainly numerical artifacts
    # or errors in the simulator's wealth process calculation.
    # We clip them to prevent mathematical divergence in summary reporting.
    rets = daily_returns.clip(-0.9999, 10.0).dropna().copy()

    # Consistent Timezone Handling - Force Naive
    try:
        new_idx = [pd.to_datetime(t).replace(tzinfo=None) for t in rets.index]
        rets.index = pd.DatetimeIndex(new_idx)
    except Exception as e_idx:
        logger.debug(f"Metrics index forcing failed: {e_idx}")
        if hasattr(rets.index, "tz") and getattr(rets.index, "tz") is not None:
            try:
                rets.index = cast(Any, rets.index).tz_convert(None)
            except AttributeError:
                rets.index = pd.to_datetime(rets.index).tz_convert(None)
        else:
            try:
                rets.index = cast(Any, rets.index).tz_localize(None)
            except AttributeError:
                rets.index = pd.to_datetime(rets.index).tz_localize(None)

    n_obs = len(rets)
    if n_obs == 0:
        return empty_res

    try:
        import quantstats as qs

        rets_j = _apply_jitter(rets)
        ann_factor = periods if periods is not None else _get_annualization_factor(rets)

        # QuantStats metrics (Proven methods)
        with np.errstate(all="ignore"):
            # Compounded total return over the period
            total_return = float(qs.stats.comp(rets))

            # Annualization
            # CR-FIX: Standardize on linear scaling for window-level reporting (Phase 225)
            # This prevents the geometric wipe-out artifact where a 10-day loss compounds to -99.99%
            if n_obs < 30:
                # LINEAR SCALING (Arithmetic Simple)
                daily_mean = float(rets.mean())
                annualized_return = daily_mean * float(ann_factor)
                vol = float(rets.std() * math.sqrt(float(ann_factor)))
                realized_vol = float(np.clip(vol, 0.0, 5.0))
                sharpe = annualized_return / (vol + 1e-9)
            else:
                # Standard geometric CAGR for long series
                total_return = float(qs.stats.comp(rets))
                annualized_return = float((1 + total_return) ** (ann_factor / n_obs)) - 1
                vol = float(qs.stats.volatility(rets, periods=ann_factor))
                realized_vol = float(np.clip(vol, 0.0, 5.0))
                sharpe = float(qs.stats.sharpe(rets, rf=0, periods=ann_factor))

            # CR-215: Dashboard Stability Clipping
            annualized_return = float(np.clip(annualized_return, -0.9999, 5.0))
            # CR-690: Institutional Sharpe Clipping (Phase 224)
            # Tightened to prevent high-Sharpe artifacts in meta-aggregation
            # But relaxed slightly for negatives to allow gradient awareness in optimizers
            sharpe = float(np.clip(sharpe, -4.0, 5.0))

            if total_return <= -0.95:
                # Force negative sharpe if portfolio is nearly dead
                sharpe = min(-5.0, sharpe)

            max_drawdown = float(qs.stats.max_drawdown(rets))

            # CR-FIX: Period Metrics (Phase 233)
            # Explicitly return period-native metrics for window analysis
            period_vol = float(rets.std() * math.sqrt(n_obs))

            return {
                "total_return": total_return,
                "period_return": total_return,
                "annualized_return": annualized_return,
                "return": annualized_return,
                "realized_vol": realized_vol,
                "period_vol": period_vol,
                "annualized_vol": realized_vol,
                "vol": realized_vol,
                "sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "mdd": max_drawdown,
                "var_95": float(qs.stats.value_at_risk(rets_j, sigma=1, confidence=0.95)),
                "cvar_95": float(qs.stats.expected_shortfall(rets_j, sigma=1, confidence=0.95)),
                "sortino": float(qs.stats.sortino(rets, rf=0, periods=ann_factor)),
                "calmar": float(qs.stats.calmar(rets, periods=ann_factor)),
                "omega": float(qs.stats.omega(rets)),
                "ann_factor": float(ann_factor),
            }
    except Exception as e:
        logger.debug(f"QuantStats failed: {e}")
        ann_factor = periods if periods is not None else _get_annualization_factor(rets)
        total_return = (1 + rets).prod() - 1

        vol_daily = float(rets.std()) if len(rets) > 1 else 0.0
        vol_ann = float(np.clip(vol_daily * math.sqrt(ann_factor), 0.0, 10.0))
        period_vol = float(vol_daily * math.sqrt(n_obs))

        if total_return <= -1.0:
            geom_mean = -1.0
            annualized_return = -1.0
            sharpe = -10.0
        else:
            geom_mean = float((1 + total_return) ** (1 / n_obs)) - 1
            annualized_return = float(np.clip((1 + geom_mean) ** ann_factor - 1, -0.9999, 100.0))
            sharpe = (rets.mean() * ann_factor) / (vol_ann + 1e-9)

        max_drawdown = calculate_max_drawdown(rets)
        return {
            "total_return": float(total_return),
            "period_return": float(total_return),
            "annualized_return": float(annualized_return),
            "return": float(annualized_return),
            "realized_vol": vol_ann,
            "annualized_vol": vol_ann,
            "period_vol": period_vol,
            "vol": vol_ann,
            "sharpe": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "mdd": float(max_drawdown),
            "ann_factor": float(ann_factor),
        }


def get_metrics_markdown(daily_returns: pd.Series, benchmark: Optional[pd.Series] = None) -> str:
    try:
        import quantstats as qs

        if len(daily_returns.dropna()) < MIN_OBSERVATIONS:
            return f"Insufficient data ({len(daily_returns.dropna())} obs)."
        df = qs.reports.metrics(daily_returns, benchmark=benchmark, display=False, mode="full")
        return cast(str, df.to_markdown()) if df is not None else "No metrics."
    except Exception as e:
        return f"Error: {e}"


def get_full_report_markdown(daily_returns: pd.Series, benchmark: Optional[pd.Series] = None, title: str = "Strategy", mode: str = "full") -> str:
    try:
        import quantstats as qs

        rets = daily_returns.dropna().copy()

        # Consistent Timezone Handling - Force Naive
        try:
            new_idx = [pd.to_datetime(t).replace(tzinfo=None) for t in rets.index]
            rets.index = pd.DatetimeIndex(new_idx)
        except Exception:
            # Fallback using safer casting
            idx = pd.DatetimeIndex(rets.index)
            if idx.tz is not None:
                rets.index = idx.tz_convert(None).tz_localize(None)
            else:
                rets.index = idx.tz_localize(None)

        if benchmark is not None:
            benchmark = benchmark.copy()
            try:
                new_b_idx = [pd.to_datetime(t).replace(tzinfo=None) for t in benchmark.index]
                benchmark.index = pd.DatetimeIndex(new_b_idx)
            except Exception:
                b_idx = pd.DatetimeIndex(benchmark.index)
                if b_idx.tz is not None:
                    benchmark.index = b_idx.tz_convert(None).tz_localize(None)
                else:
                    benchmark.index = b_idx.tz_localize(None)

            idx = rets.index.union(benchmark.index)
            benchmark = benchmark.reindex(idx)
            rets = rets.reindex(idx)

            # Align via intersection to avoid artificial padding (Phase 374)
            common_idx = rets.dropna().index.intersection(benchmark.dropna().index)
            benchmark = benchmark.loc[common_idx]
            rets = rets.loc[common_idx]

        n_obs = len(rets)

        md = [f"# Quantitative Strategy Tearsheet: {title}", f"Generated on: {pd.Timestamp.now()}\n"]
        md.append("## 1. Key Performance Metrics")
        if n_obs >= MIN_OBSERVATIONS:
            m_df = qs.reports.metrics(rets, benchmark=benchmark, display=False, mode=mode)
            if m_df is not None:
                m_md = m_df.to_markdown()
                if m_md:
                    md.append(cast(str, m_md))
        else:
            md.append(f"Insufficient data ({n_obs} observations).")

        if mode == "full" and n_obs >= MIN_OBSERVATIONS:
            md.append("\n## 2. Monthly Returns (%)")
            monthly = qs.stats.monthly_returns(rets)
            if monthly is not None:
                mon_md = (monthly * 100).round(2).to_markdown()
                if mon_md:
                    md.append(cast(str, mon_md))

            md.append("\n## 3. Annual Performance")
            dti = pd.to_datetime(rets.index)
            yearly = rets.groupby(getattr(dti, "year")).apply(qs.stats.comp)
            if not yearly.empty:
                yearly_df = pd.DataFrame({"Return (%)": (yearly * 100).round(2)})
                yearly_md = yearly_df.to_markdown()
                if yearly_md:
                    md.append(cast(str, yearly_md))

            md.append("\n## 4. Stress Audit: Worst 5 Drawdowns")
            dd_details = qs.stats.drawdown_details(qs.stats.to_drawdown_series(rets))
            if dd_details is not None and not dd_details.empty:
                cols = [str(c) for c in dd_details.columns if "drawdown" in str(c).lower()]
                if cols:
                    dd_df = cast(pd.DataFrame, dd_details)
                    dd_sorted = dd_df.sort_values(by=[cols[0]], ascending=True)
                    dd_md = dd_sorted.head(5).to_markdown()

                    if dd_md:
                        md.append(cast(str, dd_md))

        return "\n".join(md)
    except Exception as e:
        return f"# Strategy Report: {title}\n\nError: {e}"


def calculate_temporal_fragility(sharpe_series: pd.Series) -> float:
    """Coefficient of variation of Sharpe across windows."""
    s = sharpe_series.dropna()
    if s.empty or len(s) < 2:
        return 0.0
    mean_sharpe = float(s.mean())
    if abs(mean_sharpe) < 1e-9:
        return 0.0
    return float(s.std(ddof=0) / abs(mean_sharpe))


def calculate_friction_alignment(sharpe_real: float, sharpe_ideal: float) -> float:
    """Sharpe decay ratio from idealized -> high-fidelity simulation."""
    if abs(sharpe_ideal) < 1e-9:
        return 0.0
    return float(1.0 - (sharpe_real / sharpe_ideal))


def calculate_selection_jaccard(universe_a: List[str], universe_b: List[str]) -> float:
    """Jaccard similarity between two symbol sets."""
    set_a = set(universe_a)
    set_b = set(universe_b)
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    if union == 0:
        return 1.0
    return float(intersection / union)


def calculate_antifragility_distribution(
    daily_returns: pd.Series,
    *,
    q: float = 0.95,
    min_obs: int = 100,
    min_tail: int = 10,
    eps: float = 1e-12,
) -> Dict[str, Any]:
    """Quantified antifragility from return distribution (skew + tail asymmetry)."""
    rets = daily_returns.dropna().copy()
    n_obs = int(len(rets))
    if n_obs < min_obs:
        return {"n_obs": n_obs, "is_sufficient": False}

    # Use negligible jitter to avoid tie-driven empty tails, then select tails on
    # the jittered thresholds but compute statistics on the original returns.
    rets_j = _apply_jitter(rets)

    q_hi = float(rets_j.quantile(q))
    q_lo = float(rets_j.quantile(1.0 - q))

    right_tail = rets[rets_j >= q_hi]
    left_tail = rets[rets_j <= q_lo]

    n_right = int(len(right_tail))
    n_left = int(len(left_tail))

    # Tail sufficiency should be coherent with the chosen quantile and the sample size.
    # Example: at q=0.95 with 160 observations, the expected tail size is ~8; requiring
    # 10 tail points would make the metric permanently unavailable for small smokes.
    expected_tail = max(1, int(math.floor((1.0 - float(q)) * float(n_obs))))
    min_tail_eff = min(int(min_tail), expected_tail)
    if n_right < min_tail_eff or n_left < min_tail_eff:
        return {
            "q": float(q),
            "n_obs": n_obs,
            "n_right": n_right,
            "n_left": n_left,
            "min_tail_required": int(min_tail_eff),
            "is_sufficient": False,
        }

    skew = float(rets.skew())
    tail_gain = float(right_tail.mean())
    tail_loss = float(abs(left_tail.mean()))

    if tail_gain <= 0:
        tail_asym = 0.0
    else:
        tail_asym = float(tail_gain / (tail_loss + eps))

    af_dist = float(skew + math.log(tail_asym + eps))

    return {
        "q": float(q),
        "n_obs": n_obs,
        "n_right": n_right,
        "n_left": n_left,
        "min_tail_required": int(min_tail_eff),
        "skew": skew,
        "tail_gain": tail_gain,
        "tail_loss": tail_loss,
        "tail_asym": tail_asym,
        "af_dist": af_dist,
        "is_sufficient": True,
    }


def calculate_antifragility_stress(
    strategy_returns: pd.Series,
    reference_returns: pd.Series,
    *,
    q_stress: float = 0.10,
    min_obs: int = 100,
    min_stress: int = 10,
) -> Dict[str, Any]:
    """Quantified antifragility from stress response vs a reference baseline."""
    strat = strategy_returns.dropna().copy()
    ref = reference_returns.dropna().copy()

    idx = strat.index.intersection(ref.index)
    if idx.empty:
        return {"n_obs": 0, "is_sufficient": False}

    strat = strat.reindex(idx)
    ref = ref.reindex(idx)

    n_obs = int(len(idx))
    if n_obs < min_obs:
        return {"n_obs": n_obs, "is_sufficient": False}

    stress_cut = float(ref.quantile(q_stress))
    stress_mask = ref <= stress_cut
    n_stress = int(stress_mask.sum())
    if n_stress < min_stress:
        return {"q_stress": float(q_stress), "n_obs": n_obs, "n_stress": n_stress, "is_sufficient": False}

    diff = strat - ref

    stress_alpha = float(diff[stress_mask].mean())
    calm_alpha = float(diff[~stress_mask].mean())
    stress_delta = float(stress_alpha - calm_alpha)

    stress_mean = float(strat[stress_mask].mean())
    calm_mean = float(strat[~stress_mask].mean())

    stress_hit_rate = float((strat[stress_mask] > ref[stress_mask]).mean())

    return {
        "q_stress": float(q_stress),
        "n_obs": n_obs,
        "n_stress": n_stress,
        "stress_alpha": stress_alpha,
        "calm_alpha": calm_alpha,
        "stress_delta": stress_delta,
        "stress_mean": stress_mean,
        "calm_mean": calm_mean,
        "stress_hit_rate": stress_hit_rate,
        "is_sufficient": True,
    }
