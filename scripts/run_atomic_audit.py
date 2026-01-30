import argparse
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.append(os.getcwd())

from scripts.audit_directional_sign_test import run_sign_test_for_run_dir, write_findings_json
from scripts.validate_atomic_run import validate_atomic_run
from tradingview_scraper.settings import get_settings


def _resolve_run_dir(run_id: str) -> Path:
    settings = get_settings()
    runs_dir = settings.summaries_runs_dir.resolve()
    candidate = runs_dir / run_id
    if candidate.exists():
        return candidate

    matches = sorted([p for p in runs_dir.glob(f"*{run_id}*") if p.is_dir()], key=lambda p: p.name, reverse=True)
    if matches:
        return matches[0]

    raise FileNotFoundError(str(candidate))


def run_atomic_audit(
    *,
    run_id: str,
    profile: str,
    manifest_path: Optional[Path] = None,
    risk_profile: str = "hrp",
) -> int:
    run_dir = _resolve_run_dir(run_id)
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Always compute sign tests as a deterministic audit output (non-destructive: *_audit.json).
    pre = run_sign_test_for_run_dir(run_dir, atol=0.0, require_optimizer_normalization=False, risk_profile=risk_profile)
    post = run_sign_test_for_run_dir(run_dir, atol=0.0, require_optimizer_normalization=True, risk_profile=risk_profile)

    write_findings_json(pre, data_dir / "directional_sign_test_pre_opt_audit.json")
    write_findings_json(post, data_dir / "directional_sign_test_audit.json")

    sign_failed = any(f.level == "ERROR" for f in post) or any(f.level == "ERROR" for f in pre)
    rc_validate = int(validate_atomic_run(run_id=run_dir.name, profile=profile, manifest_path=manifest_path))
    return 1 if sign_failed or rc_validate != 0 else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit an atomic sleeve run (sign test + atomic validator)")
    parser.add_argument("--run-id", required=True, help="Atomic run id (or substring)")
    parser.add_argument("--profile", required=True, help="Profile name (e.g. binance_spot_rating_all_short)")
    parser.add_argument("--manifest-path", default=None, help="Manifest path (defaults to settings.manifest_path)")
    parser.add_argument("--risk-profile", default="hrp", help="Risk profile for optimizer normalization sanity (default: hrp)")
    args = parser.parse_args()

    raise SystemExit(
        run_atomic_audit(
            run_id=str(args.run_id),
            profile=str(args.profile),
            manifest_path=Path(args.manifest_path) if args.manifest_path else None,
            risk_profile=str(args.risk_profile),
        )
    )
