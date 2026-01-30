import argparse
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.metrics import (
    calculate_friction_alignment,
    calculate_selection_jaccard,
    calculate_temporal_fragility,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("tournament_scoreboard")


@dataclass(frozen=True)
class CandidateThresholds:
    max_friction_decay: float = 0.30
    max_temporal_fragility: float = 1.50
    min_selection_jaccard: float = 0.30
    # Institutional default (Jan 2026): `af_dist` is skew-dominated, so `0.0` acts
    # like a strict "positive skew required" gate. `-0.2` admits barbell-like
    # profiles in stability-default (`180/40/20`) runs while still excluding the
    # baseline `market` antifragility signature (~ -0.55 to -0.60).
    min_af_dist: float = -0.20
    min_stress_alpha: float = 0.00
    max_turnover: float = 0.50
    max_tail_multiplier: float = 1.25
    max_parity_ann_return_gap: float = 0.015

    # Sleeve-specific relaxations (ISS-008)
    max_tail_multiplier_commodity: float = 3.0
    max_parity_gap_commodity: float = 0.05


def _safe_float(val: Any) -> Optional[float]:
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        if isinstance(val, (int, float, np.number)):
            return float(val)
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return None
            return float(s)
        return float(val)
    except Exception:
        return None


def _detect_latest_run() -> Optional[str]:
    runs_dir = Path("artifacts/summaries/runs/")
    if not runs_dir.exists():
        return None
    date_pattern = re.compile(r"^\d{8}-\d{6}$")
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir() and not d.is_symlink() and date_pattern.match(d.name)]
    complete = [
        d
        for d in run_dirs
        if (d / "audit.jsonl").exists() and ((d / "grand_4d_tournament_results.json").exists() or (d / "data" / "tournament_results.json").exists() or (d / "tournament_results.json").exists())
    ]
    candidates = complete or run_dirs
    candidates = sorted(candidates, key=lambda p: p.name)
    return candidates[-1].name if candidates else None


def _iter_recent_run_ids(*, limit: int = 20) -> List[str]:
    runs_dir = Path("artifacts/summaries/runs/")
    if not runs_dir.exists():
        return []
    date_pattern = re.compile(r"^\d{8}-\d{6}$")
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir() and not d.is_symlink() and date_pattern.match(d.name)]
    run_ids = sorted([d.name for d in run_dirs])
    return run_ids[-limit:]


def _baseline_temporal_fragility_medians(scoreboard_csv: Path) -> Dict[str, float]:
    """Baseline temporal_fragility per profile, aggregated as median across simulators."""
    try:
        df = pd.read_csv(scoreboard_csv)
    except Exception:
        return {}

    if df.empty or "temporal_fragility" not in df.columns:
        return {}

    base = df[(df["engine"] == "market") & (df["profile"].isin(["market", "raw_pool_ew"]))].copy()
    if base.empty:
        return {}

    out: Dict[str, float] = {}
    for prof in ["market", "raw_pool_ew"]:
        vals = base[base["profile"] == prof]["temporal_fragility"].dropna()
        if not vals.empty:
            out[prof] = float(np.median(vals.astype(float).values))
    return out


def _auto_calibrate_max_temporal_fragility(
    *,
    n_runs: int,
    pctl: float,
    raw_blowup_cutoff: float,
    margin: float,
    current_run_id: str,
) -> Optional[float]:
    """Auto-derive a temporal fragility gate from the latest N runs.

    Percentile reference anchored to baseline rows:
    - `market` baseline: always included.
    - `raw_pool_ew` baseline: included only when not in a CV blow-up regime (median <= cutoff).
    """
    if n_runs <= 0:
        return None

    # Iterate backwards from newest. Use a larger scan window to tolerate missing scoreboards.
    recent = list(reversed(_iter_recent_run_ids(limit=max(50, n_runs * 5))))
    # Avoid leakage from the run being scored if its scoreboard already exists.
    recent = [r for r in recent if str(r) != str(current_run_id)]

    market_vals: List[float] = []
    raw_vals: List[float] = []

    for rid in recent:
        scoreboard = Path(f"artifacts/summaries/runs/{rid}/data/tournament_scoreboard.csv")
        if not scoreboard.exists():
            continue
        meds = _baseline_temporal_fragility_medians(scoreboard)
        m = meds.get("market")
        r = meds.get("raw_pool_ew")
        if m is not None:
            market_vals.append(float(m))
        if r is not None and float(r) <= raw_blowup_cutoff:
            raw_vals.append(float(r))

        if len(market_vals) >= n_runs and len(raw_vals) >= n_runs:
            break

    # Require at least a small minimum history for calibration to be meaningful.
    if len(market_vals) < max(3, min(n_runs, 5)):
        return None

    f_mkt = float(np.percentile(np.array(market_vals, dtype=float), pctl))
    if raw_vals:
        f_raw = float(np.percentile(np.array(raw_vals, dtype=float), pctl))
        base = max(f_mkt, f_raw)
    else:
        base = f_mkt

    return float(base + float(margin))


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r") as f:
        return cast_json_obj(json.load(f))


def cast_json_obj(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}


def _load_run_context_from_audit(audit_path: Path) -> Tuple[Optional[str], Optional[str]]:
    if not audit_path.exists():
        return None, None
    try:
        with open(audit_path, "r") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("step") == "backtest_simulate" and rec.get("status") == "success":
                    ctx = rec.get("context", {}) or {}
                    return ctx.get("selection_mode"), ctx.get("rebalance_mode")
    except Exception:
        return None, None
    return None, None


def _iter_result_blobs(
    payload: Dict[str, Any],
    *,
    default_selection: Optional[str],
    default_rebalance: Optional[str],
) -> Iterable[Tuple[str, str, Dict[str, Any]]]:
    """Yields (selection_mode, rebalance_mode, results_dict)."""
    if "rebalance_audit_results" in payload:
        results = payload.get("rebalance_audit_results") or {}
        if not isinstance(results, dict):
            return
        for rebalance_mode, selections in results.items():
            if not isinstance(selections, dict):
                continue
            for selection_mode, simulators in selections.items():
                if isinstance(simulators, dict):
                    yield str(selection_mode), str(rebalance_mode), simulators
        return

    # Standard tournament_results.json
    results = payload.get("results") or {}
    if not isinstance(results, dict):
        return
    yield str(default_selection or "N/A"), str(default_rebalance or "N/A"), results


def _load_returns_series(returns_dir: Path, key: str) -> Optional[pd.Series]:
    path = returns_dir / f"{key}.pkl"
    if not path.exists():
        return None
    try:
        s = pd.read_pickle(path)
        if isinstance(s, pd.Series):
            s.index = pd.to_datetime(s.index)
            s = s.dropna()
            # Overlapping walk-forward windows can create duplicate timestamps when
            # per-window return segments are concatenated. Prefer the last value.
            if s.index.has_duplicates:
                s = s[~s.index.duplicated(keep="last")]
            return s.sort_index()
    except Exception:
        return None
    return None


def _beta_corr(x: pd.Series, y: pd.Series) -> Tuple[Optional[float], Optional[float]]:
    # Defensive: overlapping windows can introduce duplicate timestamps.
    if x.index.has_duplicates:
        x = x[~x.index.duplicated(keep="last")].sort_index()
    if y.index.has_duplicates:
        y = y[~y.index.duplicated(keep="last")].sort_index()

    idx = x.index.intersection(y.index)
    if idx.empty:
        return None, None
    x2 = x.reindex(idx).dropna()
    y2 = y.reindex(idx).dropna()
    idx2 = x2.index.intersection(y2.index)
    if idx2.empty or len(idx2) < 10:
        return None, None
    x2 = x2.reindex(idx2)
    y2 = y2.reindex(idx2)

    corr = _safe_float(x2.corr(y2))
    var = _safe_float(float(np.var(y2)))
    if var is None or var <= 0:
        return None, corr
    cov = _safe_float(float(np.mean((x2 - x2.mean()) * (y2 - y2.mean()))))
    if cov is None:
        return None, corr
    beta = float(cov / var)
    return beta, corr


def _windows_return_series(windows: List[Dict[str, Any]]) -> Optional[pd.Series]:
    rows = []
    for w in windows:
        if not isinstance(w, dict):
            continue
        r = _safe_float(w.get("returns"))
        end = w.get("end_date") or w.get("start_date")
        if r is None or not end:
            continue
        try:
            t = pd.to_datetime(end)
        except Exception:
            continue
        rows.append((t, r))
    if not rows:
        return None
    rows = sorted(rows, key=lambda x: x[0])
    s = pd.Series([r for _, r in rows], index=pd.DatetimeIndex([t for t, _ in rows])).dropna()
    if s.index.has_duplicates:
        s = s[~s.index.duplicated(keep="last")]
    return s.sort_index()


def _regime_stats(windows: List[Dict[str, Any]], *, regime_key: str = "regime") -> Dict[str, Any]:
    rows = []
    for w in windows:
        if not isinstance(w, dict):
            continue
        r = _safe_float(w.get("returns"))
        regime = w.get(regime_key)
        if r is None or not regime:
            continue
        rows.append({"regime": str(regime), "returns": float(r)})
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    by = df.groupby("regime")["returns"].mean()
    worst_regime = cast_optional_str(by.idxmin())
    worst_mean = _safe_float(by.min())
    return {"worst_regime": worst_regime, "worst_regime_mean_return": worst_mean}


def cast_optional_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    try:
        s = str(val)
        return s if s else None
    except Exception:
        return None


def _as_config_key(idx: Any) -> Optional[Tuple[str, str, str, str]]:
    if not isinstance(idx, tuple) or len(idx) != 4:
        return None
    a, b, c, d = idx
    return (str(a), str(b), str(c), str(d))


def _load_optimize_metrics(audit_path: Path) -> Dict[Tuple[str, str, str, str], Dict[str, Any]]:
    """Returns per (selection, rebalance, engine, profile) metrics from backtest_optimize outcomes."""
    if not audit_path.exists():
        return {}

    buckets: Dict[Tuple[str, str, str, str], Dict[int, Dict[str, float]]] = {}

    with open(audit_path, "r") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("step") != "backtest_optimize" or rec.get("status") != "success":
                continue
            ctx = rec.get("context", {}) or {}
            selection = str(ctx.get("selection_mode", "N/A"))
            rebalance = str(ctx.get("rebalance_mode", "N/A"))
            engine = str(ctx.get("engine", ""))
            profile = str(ctx.get("profile", ""))
            if not engine or not profile:
                continue

            w_index = ctx.get("window_index")
            if w_index is None:
                continue
            try:
                window_index = int(str(w_index))
            except Exception:
                continue

            payload = rec.get("data", {}) or {}
            weights = payload.get("weights") or {}
            if not isinstance(weights, dict) or not weights:
                continue

            weights_f: Dict[str, float] = {}
            for k, v in weights.items():
                w = _safe_float(v)
                if w is None:
                    continue
                weights_f[str(k)] = float(w)
            if not weights_f:
                continue

            key = (selection, rebalance, engine, profile)
            buckets.setdefault(key, {})[window_index] = weights_f

    out: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for key, by_window in buckets.items():
        ordered = [by_window[i] for i in sorted(by_window.keys())]
        winners = [list(w.keys()) for w in ordered]

        jaccards = []
        for i in range(1, len(winners)):
            jaccards.append(calculate_selection_jaccard(winners[i - 1], winners[i]))
        avg_jaccard = float(np.mean(jaccards)) if jaccards else 1.0

        hhis = []
        max_ws = []
        n_assets = []
        for w in ordered:
            vals = np.array(list(w.values()), dtype=float)
            if vals.size == 0:
                continue
            hhis.append(float(np.sum(vals**2)))
            max_ws.append(float(np.max(vals)))
            n_assets.append(int(vals.size))

        out[key] = {
            "selection_jaccard": avg_jaccard,
            "hhi": float(np.mean(hhis)) if hhis else None,
            "max_weight": float(np.mean(max_ws)) if max_ws else None,
            "n_assets": float(np.mean(n_assets)) if n_assets else None,
        }

    return out


def _assess_candidate(row: Dict[str, Any], t: CandidateThresholds, *, allow_missing: bool) -> Tuple[bool, List[str]]:
    failures: List[str] = []

    is_commodity = bool(row.get("is_commodity", False))
    t_tail = t.max_tail_multiplier_commodity if is_commodity else t.max_tail_multiplier
    t_parity = t.max_parity_gap_commodity if is_commodity else t.max_parity_ann_return_gap

    def req(name: str) -> Optional[float]:
        v = _safe_float(row.get(name))
        if v is None and not allow_missing:
            failures.append(f"missing:{name}")
        return v

    friction_decay = req("friction_decay")
    if friction_decay is not None and friction_decay > t.max_friction_decay:
        failures.append("friction_decay")

    temporal_fragility = req("temporal_fragility")
    if temporal_fragility is not None and temporal_fragility > t.max_temporal_fragility:
        failures.append("temporal_fragility")

    selection_jaccard = req("selection_jaccard")
    if selection_jaccard is not None and selection_jaccard < t.min_selection_jaccard:
        failures.append("selection_jaccard")

    af_dist = req("af_dist")
    if af_dist is not None and af_dist < t.min_af_dist:
        failures.append("af_dist")

    stress_alpha = req("stress_alpha")
    if stress_alpha is not None and stress_alpha < t.min_stress_alpha:
        failures.append("stress_alpha")

    turnover = req("avg_turnover")
    if turnover is not None and turnover > t.max_turnover:
        failures.append("turnover")

    cvar_mult = req("cvar_mult")
    if cvar_mult is not None and cvar_mult > t_tail:
        failures.append("cvar_mult")

    mdd_mult = req("mdd_mult")
    if mdd_mult is not None and mdd_mult > t_tail:
        failures.append("mdd_mult")

    parity_gap = req("parity_ann_return_gap")
    if parity_gap is not None and parity_gap > t_parity:
        failures.append("sim_parity")

    prof = str(row.get("profile", ""))
    if prof == "min_variance":
        beta = req("beta")
        if beta is not None and beta > 0.5:
            failures.append("beta")

    return len(failures) == 0, failures


def build_scoreboard(
    results: Dict[str, Any],
    *,
    selection_mode: str,
    rebalance_mode: str,
    audit_opt: Dict[Tuple[str, str, str, str], Dict[str, Any]],
    returns_dir: Optional[Path],
    thresholds: CandidateThresholds,
    allow_missing: bool,
) -> pd.DataFrame:
    # Baseline market summaries and windows by simulator
    baseline_summary: Dict[str, Dict[str, Any]] = {}
    baseline_windows: Dict[str, List[Dict[str, Any]]] = {}

    for sim, sim_blob in results.items():
        if not isinstance(sim_blob, dict):
            continue
        eng_blob = sim_blob.get("market")
        if isinstance(eng_blob, dict):
            prof_blob = eng_blob.get("market")
            if isinstance(prof_blob, dict):
                summary = prof_blob.get("summary")
                windows = prof_blob.get("windows")
                if isinstance(summary, dict):
                    baseline_summary[str(sim)] = summary
                if isinstance(windows, list):
                    baseline_windows[str(sim)] = windows

    rows: List[Dict[str, Any]] = []

    for sim, sim_blob in results.items():
        if not isinstance(sim_blob, dict):
            continue
        for eng, eng_blob in sim_blob.items():
            if eng == "_status" or not isinstance(eng_blob, dict):
                continue
            for prof, prof_blob in eng_blob.items():
                if prof == "_status" or not isinstance(prof_blob, dict):
                    continue
                summary = prof_blob.get("summary")
                windows = prof_blob.get("windows")
                if not isinstance(summary, dict) or not isinstance(windows, list) or not windows:
                    continue

                dist = summary.get("antifragility_dist") or {}
                stress = summary.get("antifragility_stress") or {}

                # Detect commodity sleeve
                is_commodity = False
                commodity_keywords = {"GLD", "SLV", "USO", "DBC", "DBB", "CPER", "DBA", "COMMODITY"}
                # Check top_assets in windows[0]
                sample_assets = []
                if windows and isinstance(windows[0], dict):
                    sample_assets = [str(a.get("Symbol", "")) for a in windows[0].get("top_assets", [])]
                if any(any(k in s for k in commodity_keywords) for s in sample_assets):
                    is_commodity = True

                row: Dict[str, Any] = {
                    "selection": selection_mode,
                    "rebalance": rebalance_mode,
                    "engine": str(eng),
                    "profile": str(prof),
                    "simulator": str(sim),
                    "is_commodity": is_commodity,
                    "avg_window_sharpe": _safe_float(summary.get("avg_window_sharpe")),
                    "annualized_return": _safe_float(summary.get("annualized_return")),
                    "annualized_vol": _safe_float(summary.get("annualized_vol")),
                    "max_drawdown": _safe_float(summary.get("max_drawdown")),
                    "cvar_95": _safe_float(summary.get("cvar_95")),
                    "avg_turnover": _safe_float(summary.get("avg_turnover")),
                    "af_dist": _safe_float(dist.get("af_dist")) if isinstance(dist, dict) else None,
                    "stress_alpha": _safe_float(stress.get("stress_alpha")) if isinstance(stress, dict) else None,
                    "stress_delta": _safe_float(stress.get("stress_delta")) if isinstance(stress, dict) else None,
                    "stress_ref": cast_optional_str(stress.get("reference")) if isinstance(stress, dict) else None,
                }

                sharpe_series = pd.Series([_safe_float(w.get("sharpe")) for w in windows]).dropna()
                row["temporal_fragility"] = calculate_temporal_fragility(sharpe_series)

                # Prefer realized regime labels if they are available and non-null;
                # fall back to decision-time regime labels otherwise.
                use_realized = any(isinstance(w, dict) and ("realized_regime" in w) and (w.get("realized_regime") is not None) for w in windows)
                row.update(_regime_stats(windows, regime_key="realized_regime" if use_realized else "regime"))

                base = baseline_summary.get(str(sim), {})
                base_cvar = _safe_float(base.get("cvar_95"))
                base_mdd = _safe_float(base.get("max_drawdown"))
                cvar_95 = _safe_float(row.get("cvar_95"))
                if cvar_95 is not None and base_cvar is not None and base_cvar != 0.0:
                    row["cvar_mult"] = float(abs(cvar_95) / (abs(base_cvar) + 1e-12))
                max_drawdown = _safe_float(row.get("max_drawdown"))
                if max_drawdown is not None and base_mdd is not None and base_mdd != 0.0:
                    row["mdd_mult"] = float(abs(max_drawdown) / (abs(base_mdd) + 1e-12))

                # Beta/correlation: prefer daily returns pickles, fall back to window returns.
                beta, corr = None, None
                if returns_dir is not None:
                    strat_key = f"{sim}_{eng}_{prof}"
                    mkt_key = f"{sim}_market_market"
                    strat_s = _load_returns_series(returns_dir, strat_key)
                    mkt_s = _load_returns_series(returns_dir, mkt_key)
                    if strat_s is not None and mkt_s is not None:
                        beta, corr = _beta_corr(strat_s, mkt_s)
                if beta is None or corr is None:
                    strat_w = _windows_return_series(windows)
                    base_w = _windows_return_series(baseline_windows.get(str(sim), []))
                    if strat_w is not None and base_w is not None:
                        beta, corr = _beta_corr(strat_w, base_w)
                row["beta"] = beta
                row["corr"] = corr

                key = (selection_mode, rebalance_mode, str(eng), str(prof))
                opt = audit_opt.get(key)
                if opt:
                    row["selection_jaccard"] = _safe_float(opt.get("selection_jaccard"))
                    row["hhi"] = _safe_float(opt.get("hhi"))
                    row["max_weight"] = _safe_float(opt.get("max_weight"))
                    row["n_assets"] = _safe_float(opt.get("n_assets"))

                rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    df["is_baseline"] = (df["engine"].astype(str) == "market") & df["profile"].astype(str).isin(["market", "benchmark", "raw_pool_ew"])
    df["baseline_role"] = None
    mkt = df["engine"].astype(str) == "market"
    df.loc[mkt & (df["profile"].astype(str) == "benchmark"), "baseline_role"] = "anchor"
    df.loc[mkt & (df["profile"].astype(str) == "market"), "baseline_role"] = "baseline"
    df.loc[mkt & (df["profile"].astype(str) == "raw_pool_ew"), "baseline_role"] = "calibration"

    # Cross-simulator gates computed per (selection, rebalance, engine, profile)
    def _pivot_metric(metric: str) -> pd.DataFrame:
        return df.pivot_table(index=["selection", "rebalance", "engine", "profile"], columns="simulator", values=metric, aggfunc="first")

    sharpe_p = _pivot_metric("avg_window_sharpe")
    ret_p = _pivot_metric("annualized_return")

    friction_decay: Dict[Tuple[str, str, str, str], float] = {}
    if "custom" in sharpe_p.columns and "cvxportfolio" in sharpe_p.columns:
        for idx, row_vals in sharpe_p.iterrows():
            idx_key = _as_config_key(idx)
            if idx_key is None:
                continue
            s_custom = _safe_float(row_vals.get("custom"))
            s_cvx = _safe_float(row_vals.get("cvxportfolio"))
            if s_custom is None or s_cvx is None:
                continue
            friction_decay[idx_key] = calculate_friction_alignment(s_cvx, s_custom)

    parity_gap: Dict[Tuple[str, str, str, str], float] = {}
    if "cvxportfolio" in ret_p.columns and "nautilus" in ret_p.columns:
        for idx, row_vals in ret_p.iterrows():
            idx_key = _as_config_key(idx)
            if idx_key is None:
                continue
            r_cvx = _safe_float(row_vals.get("cvxportfolio"))
            r_nau = _safe_float(row_vals.get("nautilus"))
            if r_cvx is None or r_nau is None:
                continue
            parity_gap[idx_key] = float(abs(r_cvx - r_nau))

    df["friction_decay"] = df.apply(lambda r: friction_decay.get((str(r["selection"]), str(r["rebalance"]), str(r["engine"]), str(r["profile"]))), axis=1)
    df["parity_ann_return_gap"] = df.apply(lambda r: parity_gap.get((str(r["selection"]), str(r["rebalance"]), str(r["engine"]), str(r["profile"]))), axis=1)

    # Candidate flag
    flags = df.apply(lambda r: _assess_candidate(r.to_dict(), thresholds, allow_missing=allow_missing), axis=1)
    df["is_candidate"] = [bool(x[0]) for x in flags]
    df["candidate_failures"] = [";".join(x[1]) for x in flags]

    # Default sort: focus on high-fidelity simulator if present, else overall.
    df = df.sort_values(["is_candidate", "avg_window_sharpe"], ascending=[False, False])

    return df


def _to_markdown_table(df: pd.DataFrame) -> str:
    try:
        return str(df.to_markdown(index=False))
    except ImportError:
        if df.empty:
            return "_(empty)_"

        cols = [str(c) for c in df.columns]
        raw_rows = df.astype(object).values.tolist()

        def _cell(x: Any) -> str:
            if x is None:
                return ""
            if isinstance(x, float) and np.isnan(x):
                return ""
            return str(x)

        rows = [[_cell(x) for x in row] for row in raw_rows]
        widths = [max(len(cols[i]), *(len(r[i]) for r in rows)) for i in range(len(cols))]

        def _fmt_row(items: List[str]) -> str:
            return "| " + " | ".join(items[i].ljust(widths[i]) for i in range(len(cols))) + " |"

        header = _fmt_row(cols)
        sep = "| " + " | ".join("-" * widths[i] for i in range(len(cols))) + " |"
        body = "\n".join(_fmt_row(r) for r in rows)
        return "\n".join([header, sep, body])


def _write_markdown(df: pd.DataFrame, out_path: Path, *, thresholds: CandidateThresholds) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    md = ["# Tournament Scoreboard", f"Generated on: {pd.Timestamp.now()}", "", "## Thresholds", ""]
    md.append(
        _to_markdown_table(
            pd.DataFrame(
                [
                    {"Key": "max_friction_decay", "Value": thresholds.max_friction_decay},
                    {"Key": "max_temporal_fragility", "Value": thresholds.max_temporal_fragility},
                    {"Key": "min_selection_jaccard", "Value": thresholds.min_selection_jaccard},
                    {"Key": "min_af_dist", "Value": thresholds.min_af_dist},
                    {"Key": "min_stress_alpha", "Value": thresholds.min_stress_alpha},
                    {"Key": "max_turnover", "Value": thresholds.max_turnover},
                    {"Key": "max_tail_multiplier", "Value": thresholds.max_tail_multiplier},
                    {"Key": "max_parity_ann_return_gap", "Value": thresholds.max_parity_ann_return_gap},
                    {"Key": "max_tail_multiplier_commodity", "Value": thresholds.max_tail_multiplier_commodity},
                    {"Key": "max_parity_gap_commodity", "Value": thresholds.max_parity_gap_commodity},
                ]
            )
        )
    )

    cand = df[df["is_candidate"]].copy()
    is_baseline = cand.get("is_baseline", pd.Series(False, index=cand.index)).astype(bool)
    base_cand = cand[is_baseline].copy()
    strat_cand = cand[~is_baseline].copy()

    md.append("\n## Candidate Summary")
    md.append(f"- Total candidate rows: {len(cand)}")
    md.append(f"- Non-baseline candidate rows: {len(strat_cand)}")
    md.append(f"- Baseline candidate rows: {len(base_cand)}")

    md.append("\n## Top Candidates (Non-Baseline)")
    top = strat_cand.head(50)
    if top.empty:
        md.append("No non-baseline candidates passed all gates.")
    else:
        cols = [
            "selection",
            "rebalance",
            "simulator",
            "engine",
            "profile",
            "avg_window_sharpe",
            "annualized_return",
            "max_drawdown",
            "avg_turnover",
            "friction_decay",
            "temporal_fragility",
            "selection_jaccard",
            "af_dist",
            "stress_alpha",
            "cvar_mult",
            "mdd_mult",
            "parity_ann_return_gap",
        ]
        cols = [c for c in cols if c in top.columns]
        md.append(_to_markdown_table(top.loc[:, cols]))

    md.append("\n## Baseline Reference Rows")
    base = df[df.get("is_baseline", pd.Series(False, index=df.index)).astype(bool)].copy()
    if base.empty:
        md.append("No baseline rows present in the scoreboard payload.")
    else:
        # Surface baseline status prominently: these rows should be treated as reference anchors/calibration,
        # not as "winners" in downstream ranking.
        cols = [
            "selection",
            "rebalance",
            "simulator",
            "engine",
            "profile",
            "baseline_role",
            "is_candidate",
            "candidate_failures",
            "avg_window_sharpe",
            "annualized_return",
            "max_drawdown",
            "avg_turnover",
            "friction_decay",
            "temporal_fragility",
            "selection_jaccard",
            "af_dist",
            "stress_alpha",
            "cvar_mult",
            "mdd_mult",
            "parity_ann_return_gap",
        ]
        cols = [c for c in cols if c in base.columns]
        md.append(_to_markdown_table(base.loc[:, cols]))

    md.append("\n## Full Scoreboard (Top 200 by candidate then Sharpe)")
    md.append(_to_markdown_table(df.head(200)))

    out_path.write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None, help="Run ID (YYYYMMDD-HHMMSS) or 'latest'")
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--max-friction-decay", type=float, default=CandidateThresholds.max_friction_decay)
    parser.add_argument("--max-temporal-fragility", type=float, default=None, help="Override max temporal fragility gate (disables auto-calibration).")
    parser.add_argument("--calibration-runs", type=int, default=8, help="Latest-N runs used for temporal fragility auto-calibration.")
    parser.add_argument("--calibration-percentile", type=float, default=95.0, help="Percentile used for temporal fragility calibration (e.g. 90, 95).")
    parser.add_argument("--calibration-margin", type=float, default=0.25, help="Additive margin applied after temporal fragility percentile calibration.")
    parser.add_argument("--raw-pool-blowup-cutoff", type=float, default=5.0, help="Exclude raw_pool_ew baseline medians above this cutoff when calibrating.")
    parser.add_argument("--min-selection-jaccard", type=float, default=CandidateThresholds.min_selection_jaccard)
    parser.add_argument("--min-af-dist", type=float, default=CandidateThresholds.min_af_dist)
    parser.add_argument("--min-stress-alpha", type=float, default=CandidateThresholds.min_stress_alpha)
    parser.add_argument("--max-turnover", type=float, default=CandidateThresholds.max_turnover)
    parser.add_argument("--max-tail-multiplier", type=float, default=CandidateThresholds.max_tail_multiplier)
    parser.add_argument("--max-parity-gap", type=float, default=CandidateThresholds.max_parity_ann_return_gap)
    parser.add_argument("--max-tail-multiplier-commodity", type=float, default=CandidateThresholds.max_tail_multiplier_commodity)
    parser.add_argument("--max-parity-gap-commodity", type=float, default=CandidateThresholds.max_parity_gap_commodity)
    args = parser.parse_args()

    settings = get_settings()

    run_id: Optional[str] = None
    if args.run_id:
        if str(args.run_id).lower() in {"latest", "auto"}:
            run_id = None
        else:
            run_id = str(args.run_id)
    else:
        env_run_id = os.getenv("TV_RUN_ID")
        run_id = env_run_id if env_run_id else None

    if not run_id:
        run_id = _detect_latest_run()
    if not run_id:
        raise SystemExit("No run_id provided and unable to auto-detect latest run")

    settings.run_id = str(run_id)
    run_dir = settings.summaries_run_dir
    data_dir = settings.run_data_dir

    # Load the best available payload.
    payload_path = None
    if (run_dir / "grand_4d_tournament_results.json").exists():
        payload_path = run_dir / "grand_4d_tournament_results.json"
    elif (data_dir / "tournament_results.json").exists():
        payload_path = data_dir / "tournament_results.json"
    elif (run_dir / "tournament_results.json").exists():
        payload_path = run_dir / "tournament_results.json"

    if payload_path is None or not payload_path.exists():
        raise SystemExit(f"Tournament results not found for run {run_id}")

    payload = _load_json(payload_path)

    audit_path = run_dir / "audit.jsonl"
    default_selection, default_rebalance = _load_run_context_from_audit(audit_path)

    returns_dir = data_dir / "returns"
    if not returns_dir.exists() or not any(returns_dir.glob("*.pkl")):
        legacy_returns = run_dir / "returns"
        if legacy_returns.exists() and any(legacy_returns.glob("*.pkl")):
            returns_dir = legacy_returns
        else:
            returns_dir = None

    # Auto-calibrate max_temporal_fragility from latest N runs unless explicitly overridden.
    max_temporal_fragility = args.max_temporal_fragility
    if max_temporal_fragility is None:
        auto_val = _auto_calibrate_max_temporal_fragility(
            n_runs=int(args.calibration_runs),
            pctl=float(args.calibration_percentile),
            raw_blowup_cutoff=float(args.raw_pool_blowup_cutoff),
            margin=float(args.calibration_margin),
            current_run_id=str(run_id),
        )
        if auto_val is not None:
            max_temporal_fragility = float(auto_val)
            logger.info(
                "Auto-calibrated max_temporal_fragility=%.4f (runs=%d pctl=%.1f margin=%.2f raw_blowup_cutoff=%.2f)",
                max_temporal_fragility,
                int(args.calibration_runs),
                float(args.calibration_percentile),
                float(args.calibration_margin),
                float(args.raw_pool_blowup_cutoff),
            )
        else:
            max_temporal_fragility = float(CandidateThresholds.max_temporal_fragility)
            logger.info("Using default max_temporal_fragility=%.4f (insufficient history for auto-calibration).", max_temporal_fragility)

    thresholds = CandidateThresholds(
        max_friction_decay=args.max_friction_decay,
        max_temporal_fragility=float(max_temporal_fragility),
        min_selection_jaccard=args.min_selection_jaccard,
        min_af_dist=args.min_af_dist,
        min_stress_alpha=args.min_stress_alpha,
        max_turnover=args.max_turnover,
        max_tail_multiplier=args.max_tail_multiplier,
        max_parity_ann_return_gap=args.max_parity_gap,
        max_tail_multiplier_commodity=args.max_tail_multiplier_commodity,
        max_parity_gap_commodity=args.max_parity_gap_commodity,
    )

    audit_opt = _load_optimize_metrics(audit_path)

    is_grand_sweep = "rebalance_audit_results" in payload

    all_parts: List[pd.DataFrame] = []
    for sel, reb, results in _iter_result_blobs(payload, default_selection=default_selection, default_rebalance=default_rebalance):
        cell_returns_dir = returns_dir
        if is_grand_sweep:
            candidate_returns = data_dir / "grand_4d" / reb / sel / "returns"
            if candidate_returns.exists() and any(candidate_returns.glob("*.pkl")):
                cell_returns_dir = candidate_returns

        df = build_scoreboard(
            results,
            selection_mode=sel,
            rebalance_mode=reb,
            audit_opt=audit_opt,
            returns_dir=cell_returns_dir,
            thresholds=thresholds,
            allow_missing=bool(args.allow_missing),
        )
        if not df.empty:
            all_parts.append(df)

    if not all_parts:
        logger.error("No scoreboard rows produced.")
        return

    full = pd.concat(all_parts, ignore_index=True)

    out_csv = data_dir / "tournament_scoreboard.csv"
    out_candidates = data_dir / "tournament_candidates.csv"
    out_md = settings.run_reports_dir / "research" / "tournament_scoreboard.md"

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(out_csv, index=False)

    full[full["is_candidate"]].to_csv(out_candidates, index=False)
    _write_markdown(full, out_md, thresholds=thresholds)

    logger.info(f"✅ Scoreboard written: {out_csv}")
    logger.info(f"✅ Candidates written: {out_candidates}")
    logger.info(f"✅ Markdown report written: {out_md}")


if __name__ == "__main__":
    main()
