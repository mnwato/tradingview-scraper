import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


def _profile_requires_atomic_sign_gate(*, profile: str, run_dir: Path, manifest_path: Path) -> bool:
    # Priority 1: the run snapshot (what actually executed)
    snapshot = run_dir / "config" / "resolved_manifest.json"
    if snapshot.exists():
        try:
            data = _load_json(snapshot)
            feats = (data.get("features") or {}) if isinstance(data, dict) else {}
            return bool(feats.get("feat_directional_sign_test_gate_atomic"))
        except Exception:
            pass

    # Priority 2: manifest profile config (source-of-truth for future runs)
    if not manifest_path.exists():
        return False
    try:
        data = _load_json(manifest_path)
    except Exception:
        return False

    cfg = (data.get("profiles") or {}).get(profile) or {}
    feats = cfg.get("features") or {}
    return bool(feats.get("feat_directional_sign_test_gate_atomic"))


def _calendar_sanity(rets: pd.DataFrame) -> Dict[str, object]:
    idx = pd.to_datetime(rets.index)
    if idx.tz is not None:
        idx = idx.tz_convert(None)

    d = idx.normalize()
    unique_days = pd.Index(d).unique().sort_values()
    day_diffs = unique_days.to_series().diff().dropna()
    gaps = day_diffs[day_diffs > pd.Timedelta(days=1)]

    dow = unique_days.dayofweek  # Mon=0 ... Sun=6
    has_sat = bool((dow == 5).any())
    has_sun = bool((dow == 6).any())

    return {
        "n_days": int(unique_days.size),
        "has_saturday": has_sat,
        "has_sunday": has_sun,
        "n_gaps_gt_1d": int(gaps.size),
        "max_gap_days": int(gaps.max().days) if not gaps.empty else 0,
    }


def _required_artifacts(run_dir: Path) -> List[Tuple[str, Path]]:
    return [
        ("resolved_manifest", run_dir / "config" / "resolved_manifest.json"),
        ("audit_ledger", run_dir / "audit.jsonl"),
        ("returns_matrix", run_dir / "data" / "returns_matrix.parquet"),
        ("synthetic_returns", run_dir / "data" / "synthetic_returns.parquet"),
        ("portfolio_optimized_v2", run_dir / "data" / "portfolio_optimized_v2.json"),
        ("portfolio_flattened", run_dir / "data" / "portfolio_flattened.json"),
    ]


def validate_atomic_run(
    *,
    run_id: str,
    profile: str,
    output_dir: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
) -> int:
    settings = get_settings()
    m_path = manifest_path or settings.manifest_path

    run_dir = _resolve_run_dir(run_id)
    out_dir = output_dir or (run_dir / "reports" / "validation")
    out_dir.mkdir(parents=True, exist_ok=True)

    checks: List[CheckResult] = []

    # Artifact existence
    artifacts: Dict[str, object] = {}
    missing: List[str] = []
    for key, path in _required_artifacts(run_dir):
        artifacts[key] = {"path": str(path), "exists": path.exists()}
        if not path.exists():
            missing.append(f"{key}:{path.name}")
    if missing:
        checks.append(CheckResult(False, "ATOMIC_MISSING_ARTIFACTS", f"[{profile}] missing artifacts: {', '.join(missing)}"))

    require_sign_gate = _profile_requires_atomic_sign_gate(profile=profile, run_dir=run_dir, manifest_path=m_path)
    sign_pre = run_dir / "data" / "directional_sign_test_pre_opt.json"
    sign_post = run_dir / "data" / "directional_sign_test.json"

    if require_sign_gate:
        if not sign_pre.exists():
            checks.append(CheckResult(False, "ATOMIC_SIGN_TEST_PRE_MISSING", f"[{profile}] missing {sign_pre.name}"))
        else:
            try:
                payload = _load_json(sign_pre)
                if int(payload.get("errors", 1)) > 0:
                    checks.append(CheckResult(False, "ATOMIC_SIGN_TEST_PRE_FAIL", f"[{profile}] pre-opt sign test errors={int(payload.get('errors', 0))}"))
                else:
                    checks.append(CheckResult(True, "ATOMIC_SIGN_TEST_PRE_PASS", f"[{profile}] pre-opt sign test PASS"))
            except Exception:
                checks.append(CheckResult(False, "ATOMIC_SIGN_TEST_PRE_PARSE", f"[{profile}] failed to parse {sign_pre.name}"))

        if not sign_post.exists():
            checks.append(CheckResult(False, "ATOMIC_SIGN_TEST_POST_MISSING", f"[{profile}] missing {sign_post.name}"))
        else:
            try:
                payload = _load_json(sign_post)
                if int(payload.get("errors", 1)) > 0:
                    checks.append(CheckResult(False, "ATOMIC_SIGN_TEST_POST_FAIL", f"[{profile}] post-opt sign test errors={int(payload.get('errors', 0))}"))
                else:
                    checks.append(CheckResult(True, "ATOMIC_SIGN_TEST_POST_PASS", f"[{profile}] post-opt sign test PASS"))
            except Exception:
                checks.append(CheckResult(False, "ATOMIC_SIGN_TEST_POST_PARSE", f"[{profile}] failed to parse {sign_post.name}"))

    # Data sanity (crypto calendar expectation)
    stats: Dict[str, object] = {}
    returns_path = run_dir / "data" / "returns_matrix.parquet"
    if returns_path.exists():
        try:
            rets = pd.read_parquet(returns_path)
            if isinstance(rets, pd.Series):
                rets = rets.to_frame()
            if rets.empty:
                checks.append(CheckResult(False, "ATOMIC_EMPTY_RETURNS", f"[{profile}] returns_matrix.parquet is empty"))
            else:
                stats["calendar"] = _calendar_sanity(rets)
        except Exception as exc:
            checks.append(CheckResult(False, "ATOMIC_RETURNS_PARSE", f"[{profile}] failed to read returns_matrix.parquet: {exc}"))

    # Optimizer output sanity
    opt_path = run_dir / "data" / "portfolio_optimized_v2.json"
    if opt_path.exists():
        try:
            opt = _load_json(opt_path)
            profs = opt.get("profiles") or {}
            hrp = (profs.get("hrp") or {}) if isinstance(profs, dict) else {}
            assets = hrp.get("assets") or []
            if not assets:
                checks.append(CheckResult(False, "ATOMIC_EMPTY_HRP", f"[{profile}] portfolio_optimized_v2.json has no hrp assets"))
            else:
                checks.append(CheckResult(True, "ATOMIC_HRP_PRESENT", f"[{profile}] hrp assets={len(assets)}"))
        except Exception as exc:
            checks.append(CheckResult(False, "ATOMIC_OPT_PARSE", f"[{profile}] failed to parse portfolio_optimized_v2.json: {exc}"))

    # Flattened output sanity
    flat_path = run_dir / "data" / "portfolio_flattened.json"
    if flat_path.exists():
        try:
            flat = _load_json(flat_path)
            weights = flat.get("weights") or flat.get("assets") or []
            if not weights:
                checks.append(CheckResult(False, "ATOMIC_EMPTY_FLATTENED", f"[{profile}] portfolio_flattened.json has no weights"))
            else:
                checks.append(CheckResult(True, "ATOMIC_FLATTENED_PRESENT", f"[{profile}] flattened weights={len(weights)}"))
        except Exception as exc:
            checks.append(CheckResult(False, "ATOMIC_FLATTEN_PARSE", f"[{profile}] failed to parse portfolio_flattened.json: {exc}"))

    failed = [c for c in checks if not c.ok]
    summary: Dict[str, object] = {
        "run_id": run_dir.name,
        "profile": profile,
        "artifacts_dir": str(run_dir),
        "manifest_path": str(m_path),
        "require_sign_gate": require_sign_gate,
        "artifacts": artifacts,
        "stats": stats,
        "checks": [{"ok": c.ok, "code": c.code, "message": c.message} for c in checks],
    }

    out_json = out_dir / f"atomic_validation_{profile}_{run_dir.name}.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    out_md = out_dir / f"atomic_validation_{profile}_{run_dir.name}.md"
    lines: List[str] = []
    lines.append(f"# Atomic Validation: {profile}")
    lines.append("")
    lines.append(f"- Run ID: `{run_dir.name}`")
    lines.append(f"- Artifacts Dir: `{run_dir}`")
    lines.append(f"- Require Sign Gate: `{require_sign_gate}`")
    lines.append("")
    lines.append(f"## Status: {'PASS' if not failed else 'FAIL'}")
    lines.append("")
    for c in checks:
        mark = "✅" if c.ok else "❌"
        lines.append(f"- {mark} `{c.code}` {c.message}")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(out_md.read_text(encoding="utf-8"))
    print(f"Wrote `{out_json}`")

    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate an atomic sleeve run directory (artifact + sign-test checks)")
    parser.add_argument("--run-id", required=True, help="Atomic run id (or substring)")
    parser.add_argument("--profile", required=True, help="Profile name (e.g. binance_spot_rating_all_short)")
    parser.add_argument("--manifest-path", default=None, help="Manifest path (defaults to settings.manifest_path)")
    args = parser.parse_args()

    raise SystemExit(
        validate_atomic_run(
            run_id=str(args.run_id),
            profile=str(args.profile),
            manifest_path=Path(args.manifest_path) if args.manifest_path else None,
        )
    )
