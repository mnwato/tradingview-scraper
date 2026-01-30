import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd

sys.path.append(os.getcwd())
from tradingview_scraper.settings import get_settings


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    code: str
    message: str


def _load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _meta_profile_requires_sign_test(meta_profile: str, manifest_path: Path) -> bool:
    if not manifest_path.exists():
        return False
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    cfg = (data.get("profiles") or {}).get(meta_profile) or {}
    feats = cfg.get("features") or {}
    return bool(feats.get("feat_directional_sign_test_gate"))


def _load_sign_test_result(base_dir: Path) -> Optional[Dict]:
    path = base_dir / "directional_sign_test.json"
    if not path.exists():
        return None
    try:
        return _load_json(path)
    except Exception:
        return {"errors": None, "warnings": None, "findings": [], "parse_error": True}


def _summaries_run_dir() -> Path:
    settings = get_settings()
    return settings.summaries_runs_dir.resolve()


def _resolve_run_dir(run_id: str) -> Path:
    runs_dir = _summaries_run_dir()
    candidate = runs_dir / run_id
    if candidate.exists():
        return candidate

    # Allow partials (deterministic: newest lexicographically)
    matches = sorted([p for p in runs_dir.glob(f"*{run_id}*") if p.is_dir()], key=lambda p: p.name, reverse=True)
    if matches:
        return matches[0]

    raise FileNotFoundError(str(candidate))


def _iter_risk_profiles(raw: str) -> List[str]:
    items = [p.strip() for p in raw.split(",") if p.strip()]
    return items


def _physical_symbol(symbol: str) -> str:
    # Convention: atoms are `PHYSICAL_<logic>_<direction>...`
    # For physicals, leave untouched.
    return symbol.split("_", 1)[0] if "_" in symbol else symbol


def _concentration_report(weights: List[Dict]) -> Tuple[Dict[str, float], float]:
    phys = {}
    for row in weights:
        sym = row.get("Symbol", "")
        w = float(row.get("Weight", 0.0))
        phys_sym = _physical_symbol(sym)
        phys[phys_sym] = phys.get(phys_sym, 0.0) + w
    max_phys = max(phys.values()) if phys else 0.0
    return phys, max_phys


def _directional_exposure(weights: List[Dict]) -> Dict[str, float]:
    gross_long = 0.0
    gross_short = 0.0
    for row in weights:
        net = row.get("Net_Weight")
        if net is None:
            # Fallback to Direction + Weight
            direction = str(row.get("Direction", "")).upper()
            w = float(row.get("Weight", 0.0))
            if direction == "SHORT":
                gross_short += w
            else:
                gross_long += w
            continue

        net_f = float(net)
        if net_f >= 0:
            gross_long += abs(net_f)
        else:
            gross_short += abs(net_f)

    net = gross_long - gross_short
    return {"gross_long": gross_long, "gross_short": gross_short, "net": net}


def _calendar_sanity(rets: pd.DataFrame) -> Dict[str, object]:
    idx = pd.to_datetime(rets.index)
    if idx.tz is not None:
        idx = idx.tz_convert(None)

    # Cast to DatetimeIndex to satisfy static analysis for normalize/dayofweek
    dt_index = cast(pd.DatetimeIndex, idx)
    d = dt_index.normalize()
    unique_days = pd.Index(d).unique().sort_values()

    # Cast unique_days to DatetimeIndex for dayofweek
    dt_unique = cast(pd.DatetimeIndex, unique_days)
    day_diffs = dt_unique.to_series().diff().dropna()
    gaps = day_diffs[day_diffs > pd.Timedelta(days=1)]

    # For crypto-only runs we EXPECT weekend presence (Sat/Sun).
    dow = dt_unique.dayofweek  # Mon=0 ... Sun=6
    has_sat = bool((dow == 5).any())
    has_sun = bool((dow == 6).any())

    return {
        "n_days": int(dt_unique.size),
        "has_saturday": has_sat,
        "has_sunday": has_sun,
        "n_gaps_gt_1d": int(gaps.size),
        "max_gap_days": int(gaps.max().days) if not gaps.empty else 0,
    }


def _load_meta_returns(base_dir: Path, meta_profile: str, risk_profile: str) -> pd.DataFrame:
    path = base_dir / f"meta_returns_{meta_profile}_{risk_profile}.pkl"
    data = pd.read_pickle(path)
    if isinstance(data, pd.Series):
        return data.to_frame()
    return cast(pd.DataFrame, data)


def _load_meta_optimized(base_dir: Path, meta_profile: str, risk_profile: str) -> Dict:
    path = base_dir / f"meta_optimized_{meta_profile}_{risk_profile}.json"
    return _load_json(path)


def _load_flattened(base_dir: Path, meta_profile: str, risk_profile: str) -> Dict:
    path = base_dir / f"portfolio_optimized_meta_{meta_profile}_{risk_profile}.json"
    return _load_json(path)


def _load_cluster_tree(base_dir: Path, meta_profile: str, risk_profile: str) -> Dict:
    path = base_dir / f"meta_cluster_tree_{meta_profile}_{risk_profile}.json"
    return _load_json(path)


def _required_artifacts(base_dir: Path, meta_profile: str, risk_profile: str) -> List[Tuple[str, Path]]:
    return [
        ("meta_returns", base_dir / f"meta_returns_{meta_profile}_{risk_profile}.pkl"),
        ("meta_optimized", base_dir / f"meta_optimized_{meta_profile}_{risk_profile}.json"),
        ("meta_cluster_tree", base_dir / f"meta_cluster_tree_{meta_profile}_{risk_profile}.json"),
        ("portfolio_optimized_meta", base_dir / f"portfolio_optimized_meta_{meta_profile}_{risk_profile}.json"),
    ]


def validate_meta_run(
    *,
    run_id: str,
    meta_profile: str,
    risk_profiles: List[str],
    max_phys_weight: float = 0.15,
    output_dir: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
) -> int:
    from typing import Any

    run_dir = _resolve_run_dir(run_id)
    base_dir = (run_dir / "data").resolve()
    out_dir = output_dir or (run_dir / "reports" / "validation")
    out_dir.mkdir(parents=True, exist_ok=True)

    checks: List[CheckResult] = []
    settings = get_settings()
    m_path = manifest_path or settings.manifest_path
    require_sign_test = _meta_profile_requires_sign_test(meta_profile, m_path)

    if require_sign_test:
        res = _load_sign_test_result(base_dir)
        if res is None:
            checks.append(CheckResult(False, "META_SIGN_TEST_MISSING", f"[{meta_profile}] directional_sign_test.json missing in {base_dir}"))
        else:
            n_err = res.get("errors")
            if n_err is None:
                checks.append(CheckResult(False, "META_SIGN_TEST_PARSE", f"[{meta_profile}] failed to parse directional_sign_test.json"))
            elif int(n_err) > 0:
                checks.append(CheckResult(False, "META_SIGN_TEST_FAIL", f"[{meta_profile}] directional sign test has errors={int(n_err)}"))
            else:
                checks.append(CheckResult(True, "META_SIGN_TEST_PASS", f"[{meta_profile}] directional sign test PASS"))

    summary: Dict[str, Any] = {
        "run_id": run_dir.name,
        "meta_profile": meta_profile,
        "risk_profiles": risk_profiles,
        "artifacts_dir": str(base_dir),
        "manifest_path": str(m_path),
        "require_sign_test": require_sign_test,
        "results": {},
    }

    for prof in risk_profiles:
        prof_res: Dict[str, Any] = {"risk_profile": prof, "artifacts": {}, "stats": {}}

        missing = []
        for key, path in _required_artifacts(base_dir, meta_profile, prof):
            prof_res["artifacts"][key] = {"path": str(path), "exists": path.exists()}
            if not path.exists():
                missing.append(f"{key}:{path.name}")

        if missing:
            msg = f"[{meta_profile}/{prof}] missing artifacts: {', '.join(missing)}"
            checks.append(CheckResult(False, "META_MISSING_ARTIFACTS", msg))
            summary["results"][prof] = prof_res
            continue

        meta_rets = _load_meta_returns(base_dir, meta_profile, prof)
        if not isinstance(meta_rets, pd.DataFrame):
            meta_rets = pd.DataFrame(meta_rets)

        if meta_rets.empty:
            checks.append(CheckResult(False, "META_EMPTY_RETURNS", f"[{meta_profile}/{prof}] meta returns are empty"))
            summary["results"][prof] = prof_res
            continue

        opt = _load_meta_optimized(base_dir, meta_profile, prof)
        weights = opt.get("weights", [])
        if not weights:
            checks.append(CheckResult(False, "META_EMPTY_WEIGHTS", f"[{meta_profile}/{prof}] meta_optimized has no weights"))
            summary["results"][prof] = prof_res
            continue

        w_sum = float(sum(float(w.get("Weight", 0.0)) for w in weights))
        prof_res["stats"]["meta_weights_sum"] = w_sum
        prof_res["stats"]["n_sleeves"] = int(len(weights))

        # Compute a simple meta portfolio return series from the optimized sleeve weights.
        # Note: meta_rets columns are sleeve IDs (e.g. long_all, short_all).
        w_map = {str(w.get("Symbol")): float(w.get("Weight", 0.0)) for w in weights if w.get("Symbol") in meta_rets.columns}
        if not w_map:
            checks.append(CheckResult(False, "META_WEIGHT_COLUMN_MISMATCH", f"[{meta_profile}/{prof}] weights don't match meta_returns columns"))
            summary["results"][prof] = prof_res
            continue

        # Align and normalize defensively
        cols = [c for c in meta_rets.columns if c in w_map]
        w_vec = np.array([w_map[c] for c in cols], dtype=float)
        if float(w_vec.sum()) <= 0:
            checks.append(CheckResult(False, "META_BAD_WEIGHT_SUM", f"[{meta_profile}/{prof}] sleeve weight sum <= 0"))
            summary["results"][prof] = prof_res
            continue

        w_vec = w_vec / float(w_vec.sum())
        port = (meta_rets[cols] * w_vec).sum(axis=1)

        prof_res["stats"]["meta_portfolio_mean_daily"] = float(port.mean())
        prof_res["stats"]["meta_portfolio_vol_daily"] = float(port.std(ddof=0))
        prof_res["stats"]["meta_portfolio_skew"] = float(port.skew())
        prof_res["stats"]["meta_portfolio_kurtosis"] = float(port.kurtosis())
        prof_res["stats"]["meta_portfolio_var_95"] = float(port.quantile(0.05))

        prof_res["stats"]["calendar"] = _calendar_sanity(meta_rets)

        # Flattened weights: concentration + directional exposure.
        flat = _load_flattened(base_dir, meta_profile, prof)
        flat_weights = flat.get("weights", [])
        if not flat_weights:
            checks.append(CheckResult(False, "META_EMPTY_FLATTENED", f"[{meta_profile}/{prof}] flattened portfolio has no weights"))
            summary["results"][prof] = prof_res
            continue

        phys, max_phys = _concentration_report(flat_weights)
        exposure = _directional_exposure(flat_weights)
        prof_res["stats"]["n_assets_flattened"] = int(len(flat_weights))
        prof_res["stats"]["max_physical_weight"] = float(max_phys)
        prof_res["stats"]["directional_exposure"] = exposure

        top_phys = sorted(phys.items(), key=lambda kv: kv[1], reverse=True)[:10]
        prof_res["stats"]["top_physical_assets"] = [{"symbol": k, "weight": float(v)} for k, v in top_phys]

        if max_phys > max_phys_weight:
            checks.append(CheckResult(False, "META_CONCENTRATION", f"[{meta_profile}/{prof}] max physical weight {max_phys:.2%} > {max_phys_weight:.2%}"))
        else:
            checks.append(CheckResult(True, "META_CONCENTRATION", f"[{meta_profile}/{prof}] max physical weight {max_phys:.2%}"))

        # Cluster tree existence + structure sanity
        tree = _load_cluster_tree(base_dir, meta_profile, prof)
        if not tree.get("weights"):
            checks.append(CheckResult(False, "META_CLUSTER_TREE_EMPTY", f"[{meta_profile}/{prof}] cluster tree missing weights"))
        else:
            checks.append(CheckResult(True, "META_CLUSTER_TREE", f"[{meta_profile}/{prof}] cluster tree present"))

        summary["results"][prof] = prof_res

    # Write machine-readable summary
    summary["checks"] = [{"ok": c.ok, "code": c.code, "message": c.message} for c in checks]
    out_json = out_dir / f"meta_validation_{meta_profile}_{run_dir.name}.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Write a short markdown summary for humans
    out_md = out_dir / f"meta_validation_{meta_profile}_{run_dir.name}.md"
    lines: List[str] = []
    lines.append(f"# Meta Validation: {meta_profile}")
    lines.append("")
    lines.append(f"- Run ID: `{run_dir.name}`")
    lines.append(f"- Artifacts Dir: `{base_dir}`")
    lines.append(f"- Risk Profiles: `{', '.join(risk_profiles)}`")
    lines.append("")

    failed = [c for c in checks if not c.ok]
    lines.append(f"## Status: {'PASS' if not failed else 'FAIL'}")
    lines.append("")
    for c in checks:
        mark = "✅" if c.ok else "❌"
        lines.append(f"- {mark} `{c.code}` {c.message}")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Print a concise stdout summary
    print(out_md.read_text(encoding="utf-8"))
    print(f"Wrote `{out_json}`")

    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a meta-portfolio run directory (artifact + sanity checks)")
    parser.add_argument("--run-id", required=True, help="Meta run id (or substring)")
    parser.add_argument("--meta-profile", required=True, help="Meta profile name (e.g. meta_crypto_only)")
    parser.add_argument("--risk-profiles", default="hrp,min_variance,barbell", help="Comma-separated risk profiles to validate")
    parser.add_argument("--max-phys-weight", type=float, default=0.15, help="Max allowed physical asset weight (default 0.15)")
    parser.add_argument("--manifest-path", default=None, help="Manifest path (defaults to settings.manifest_path)")
    args = parser.parse_args()

    raise SystemExit(
        validate_meta_run(
            run_id=args.run_id,
            meta_profile=args.meta_profile,
            risk_profiles=_iter_risk_profiles(args.risk_profiles),
            max_phys_weight=float(args.max_phys_weight),
            manifest_path=Path(args.manifest_path) if args.manifest_path else None,
        )
    )
