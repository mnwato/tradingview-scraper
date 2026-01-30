import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

sys.path.append(os.getcwd())


@dataclass(frozen=True)
class SignTestFinding:
    level: str  # "ERROR" | "WARN"
    code: str
    run_id: str
    symbol: str
    message: str


def _load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def findings_to_dict(findings: List[SignTestFinding]) -> Dict[str, object]:
    errors = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]
    return {
        "errors": len(errors),
        "warnings": len(warns),
        "findings": [{"level": f.level, "code": f.code, "run_id": f.run_id, "symbol": f.symbol, "message": f.message} for f in findings],
    }


def write_findings_json(findings: List[SignTestFinding], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(findings_to_dict(findings), indent=2), encoding="utf-8")


def _resolve_run_dir(run_id: str) -> Path:
    from tradingview_scraper.settings import get_settings

    settings = get_settings()
    candidate = (settings.summaries_runs_dir / run_id).resolve()
    if candidate.exists():
        return candidate
    raise FileNotFoundError(str(candidate))


def _iter_synthetic_pairs(synthetic_cols: Iterable[str]) -> Iterable[Tuple[str, str, str]]:
    """Yield (atom_col, physical_symbol, direction) for *_LONG/*_SHORT synthetic columns."""
    for col in synthetic_cols:
        if not isinstance(col, str):
            continue
        if col.endswith("_LONG"):
            yield col, col.split("_", 1)[0], "LONG"
        elif col.endswith("_SHORT"):
            yield col, col.split("_", 1)[0], "SHORT"


def run_sign_test_for_run_dir(
    run_dir: Path,
    *,
    atol: float = 0.0,
    require_optimizer_normalization: bool = True,
    risk_profile: str = "hrp",
) -> List[SignTestFinding]:
    """Directional correction sign test.

    Requirement:
    - For each synthetic atom stream ending with `_SHORT`, the synthetic return series MUST
      equal `-clip(raw_returns[physical], upper=1.0)` (elementwise) at the sleeve boundary.
      This matches the synthetic short loss cap of -100% (a short cannot lose more than 100%).
    - For `_LONG`, synthetic MUST equal raw (elementwise).

    Evidence:
    - `synthetic_returns.parquet` is the atom-level matrix.
    - `returns_matrix.parquet` is the physical-asset returns matrix.
    """
    run_id = run_dir.name
    findings: List[SignTestFinding] = []

    syn_path = run_dir / "data" / "synthetic_returns.parquet"
    raw_path = run_dir / "data" / "returns_matrix.parquet"
    opt_path = run_dir / "data" / "portfolio_optimized_v2.json"

    if not syn_path.exists():
        findings.append(SignTestFinding("ERROR", "SIGNTEST_MISSING_SYNTHETIC", run_id, "N/A", f"Missing {syn_path}"))
        return findings
    if not raw_path.exists():
        findings.append(SignTestFinding("ERROR", "SIGNTEST_MISSING_RAW", run_id, "N/A", f"Missing {raw_path}"))
        return findings

    syn = pd.read_parquet(syn_path)
    raw = pd.read_parquet(raw_path)

    if syn.empty:
        findings.append(SignTestFinding("ERROR", "SIGNTEST_EMPTY_SYNTHETIC", run_id, "N/A", "synthetic_returns is empty"))
        return findings
    if raw.empty:
        findings.append(SignTestFinding("ERROR", "SIGNTEST_EMPTY_RAW", run_id, "N/A", "returns_matrix is empty"))
        return findings

    # Index alignment (inner join)
    common_idx = syn.index.intersection(raw.index)
    syn = syn.loc[common_idx]
    raw = raw.loc[common_idx]

    # Core sign checks
    checked = 0
    for atom_col, phys, direction in _iter_synthetic_pairs(syn.columns):
        if phys not in raw.columns:
            findings.append(SignTestFinding("WARN", "SIGNTEST_MISSING_PHYSICAL_COL", run_id, atom_col, f"Physical symbol {phys} missing in returns_matrix"))
            continue

        s = syn[atom_col].astype(float)
        r = raw[phys].astype(float)

        if direction == "LONG":
            ok = (s - r).abs().max() <= float(atol)
            if not ok:
                findings.append(SignTestFinding("ERROR", "SIGNTEST_LONG_MISMATCH", run_id, atom_col, f"Expected synthetic LONG == raw for {phys} (atol={atol})"))
        else:
            # Synthetic shorts are inverted, but must also respect the -100% loss cap.
            # If raw return > 1.0 (price > 2x), synthetic short return is capped at -1.0.
            expected = -r.clip(upper=1.0)
            ok = (s - expected).abs().max() <= float(atol)
            if not ok:
                findings.append(SignTestFinding("ERROR", "SIGNTEST_SHORT_NOT_INVERTED", run_id, atom_col, f"Expected synthetic SHORT == -clip(raw, upper=1.0) for {phys} (atol={atol})"))
        checked += 1

    if checked == 0:
        findings.append(SignTestFinding("WARN", "SIGNTEST_NO_ATOMS", run_id, "N/A", "No *_LONG/*_SHORT synthetic columns found"))

    # Optimizer normalization sanity: short atoms should appear as LONG weights (synthetic-long normalization).
    if require_optimizer_normalization and opt_path.exists():
        try:
            opt = _load_json(opt_path)
            assets = ((opt.get("profiles") or {}).get(risk_profile) or {}).get("assets") or []
            for a in assets:
                sym = str(a.get("Symbol", ""))
                if sym.endswith("_SHORT"):
                    direction = str(a.get("Direction", "")).upper()
                    net = float(a.get("Net_Weight", a.get("Weight", 0.0)) or 0.0)
                    if direction != "LONG" or net < -1e-12:
                        findings.append(
                            SignTestFinding(
                                "ERROR",
                                "SIGNTEST_OPTIMIZER_NOT_NORMALIZED",
                                run_id,
                                sym,
                                f"Expected SHORT atom to be normalized as LONG (Direction=LONG, Net_Weight>=0). Got Direction={direction} Net_Weight={net}",
                            )
                        )
        except Exception as exc:
            findings.append(SignTestFinding("WARN", "SIGNTEST_OPTIMIZER_PARSE", run_id, "N/A", f"Failed to parse optimizer output: {exc}"))

    return findings


def run_sign_test_for_meta_profile(meta_profile: str, *, manifest_path: Path = Path("configs/manifest.json"), risk_profile: str = "hrp", atol: float = 0.0) -> List[SignTestFinding]:
    """Audit all sleeves referenced by a meta profile in the manifest."""
    data = _load_json(manifest_path)
    prof = (data.get("profiles") or {}).get(meta_profile)
    if not isinstance(prof, dict):
        return [SignTestFinding("ERROR", "SIGNTEST_META_PROFILE_MISSING", meta_profile, "N/A", f"Meta profile not found in manifest: {meta_profile}")]

    sleeves = prof.get("sleeves") or []
    if not sleeves:
        return [SignTestFinding("ERROR", "SIGNTEST_META_NO_SLEEVES", meta_profile, "N/A", "Meta profile has no sleeves")]

    findings: List[SignTestFinding] = []
    for sleeve in sleeves:
        run_id = sleeve.get("run_id")
        if run_id:
            run_dir = _resolve_run_dir(str(run_id))
            findings.extend(run_sign_test_for_run_dir(run_dir, atol=atol, risk_profile=risk_profile))
        else:
            # No pinned run_id; can't audit deterministically.
            findings.append(
                SignTestFinding(
                    "WARN", "SIGNTEST_META_SLEEVE_NO_RUN_ID", meta_profile, str(sleeve.get("id", "unknown")), "Sleeve run_id is empty; run the sleeves first or pin run_id for auditability"
                )
            )

    return findings


def _print_findings(findings: List[SignTestFinding]) -> int:
    errors = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]

    if errors:
        print("# Directional Sign Test: FAIL\n")
    else:
        print("# Directional Sign Test: PASS\n")

    print(f"- Errors: {len(errors)}")
    print(f"- Warnings: {len(warns)}\n")

    for f in findings:
        mark = "❌" if f.level == "ERROR" else "⚠️"
        print(f"- {mark} `{f.code}` `{f.run_id}` `{f.symbol}` {f.message}")

    return 1 if errors else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Directional Correction Sign Test (SHORT inversion audit)")
    parser.add_argument("--run-id", help="Audit a single sleeve run id (artifacts/summaries/runs/<RUN_ID>)")
    parser.add_argument("--meta-profile", help="Audit all sleeves in a meta profile (configs/manifest.json)")
    parser.add_argument("--manifest-path", default="configs/manifest.json", help="Manifest path (default: configs/manifest.json)")
    parser.add_argument("--risk-profile", default="hrp", help="Risk profile for optimizer normalization sanity (default: hrp)")
    parser.add_argument("--atol", type=float, default=0.0, help="Absolute tolerance for equality checks (default: 0.0)")
    args = parser.parse_args()

    if bool(args.run_id) == bool(args.meta_profile):
        print("Provide exactly one of --run-id or --meta-profile")
        raise SystemExit(2)

    if args.run_id:
        findings = run_sign_test_for_run_dir(_resolve_run_dir(args.run_id), atol=float(args.atol), risk_profile=str(args.risk_profile))
    else:
        findings = run_sign_test_for_meta_profile(str(args.meta_profile), manifest_path=Path(args.manifest_path), risk_profile=str(args.risk_profile), atol=float(args.atol))

    raise SystemExit(_print_findings(findings))
