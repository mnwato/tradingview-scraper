import argparse
import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_FIELDS = [
    "annualized_return",
    "annualized_vol",
    "sharpe",
    "max_drawdown",
    "win_rate",
]


def _load_results(run_id: str, runs_root: Path) -> Dict[str, Any]:
    run_path = runs_root / run_id / "tournament_results.json"
    if not run_path.exists():
        raise FileNotFoundError(f"tournament_results.json not found for run {run_id}: {run_path}")
    with run_path.open("r") as f:
        return json.load(f)


def _extract_raw_pool_summary(results: Dict[str, Any], simulator: str, engine: str) -> Dict[str, Any]:
    try:
        node = results["results"][simulator][engine]["raw_pool_ew"]
    except Exception as exc:  # noqa: BLE001
        raise KeyError(f"raw_pool_ew not found for simulator={simulator}, engine={engine}") from exc

    summary = node.get("summary")
    if summary is None:
        raise ValueError(f"raw_pool_ew summary missing for simulator={simulator}, engine={engine}")

    return {
        "windows_count": len(node.get("windows") or []),
        **{field: summary.get(field) for field in DEFAULT_FIELDS},
    }


def _load_audit_metadata(run_id: str, runs_root: Path, simulator: str, engine: str) -> Dict[str, Any]:
    audit_path = runs_root / run_id / "audit.jsonl"
    if not audit_path.exists():
        raise FileNotFoundError(f"audit.jsonl not found for run {run_id}: {audit_path}")

    metadata: Dict[str, Any] = {}
    with audit_path.open("r") as f:
        for line in f:
            entry = json.loads(line)
            context = entry.get("context")
            if not context:
                continue
            if context.get("profile") != "raw_pool_ew":
                continue
            if context.get("engine") != engine or context.get("simulator") != simulator:
                continue

            metadata = {
                "selection_mode": context.get("selection_mode"),
                "universe_source": context.get("universe_source"),
                "raw_pool_returns_hash": context.get("raw_pool_returns_hash"),
                "raw_pool_symbol_count": context.get("raw_pool_symbol_count"),
            }
            break

    if not metadata:
        raise ValueError(f"raw_pool_ew metadata not found for simulator={simulator}, engine={engine} in run {run_id} audit")

    return metadata


def _diff(a: Dict[str, Any], b: Dict[str, Any], tol: float) -> Dict[str, float]:
    diffs: Dict[str, float] = {}
    for key in a:
        if key == "windows_count":
            if a[key] != b.get(key):
                diffs[key] = float("inf")
            continue
        av = a.get(key)
        bv = b.get(key)
        if av is None or bv is None:
            diffs[key] = float("inf")
            continue
        delta = abs(float(av) - float(bv))
        if delta > tol:
            diffs[key] = delta
    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(description="Guardrail for raw_pool_ew selection-mode invariance.")
    parser.add_argument("--run-a", required=True)
    parser.add_argument("--run-b", required=True)
    parser.add_argument("--runs-root", default="artifacts/summaries/runs")
    parser.add_argument("--simulator", default="custom")
    parser.add_argument("--engine", default="market")
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()

    runs_root = Path(args.runs_root)
    data_a = _load_results(args.run_a, runs_root)
    data_b = _load_results(args.run_b, runs_root)

    summary_a = _extract_raw_pool_summary(data_a, args.simulator, args.engine)
    summary_b = _extract_raw_pool_summary(data_b, args.simulator, args.engine)
    metadata_a = _load_audit_metadata(args.run_a, runs_root, args.simulator, args.engine)
    metadata_b = _load_audit_metadata(args.run_b, runs_root, args.simulator, args.engine)

    print("Run metadata:")
    print(
        f"- {args.run_a}: selection_mode={metadata_a['selection_mode']}, universe_source={metadata_a['universe_source']}, "
        f"symbols={metadata_a['raw_pool_symbol_count']}, returns_hash={metadata_a['raw_pool_returns_hash']}"
    )
    print(
        f"- {args.run_b}: selection_mode={metadata_b['selection_mode']}, universe_source={metadata_b['universe_source']}, "
        f"symbols={metadata_b['raw_pool_symbol_count']}, returns_hash={metadata_b['raw_pool_returns_hash']}"
    )

    diffs = _diff(summary_a, summary_b, args.tolerance)

    print(f"raw_pool_ew invariance check ({args.run_a} vs {args.run_b})")
    print(f"simulator={args.simulator} engine={args.engine} tolerance={args.tolerance}")
    print(json.dumps({"run_a": summary_a, "run_b": summary_b}, indent=2))

    same_universe = metadata_a["universe_source"] == metadata_b["universe_source"] and metadata_a["raw_pool_returns_hash"] == metadata_b["raw_pool_returns_hash"]
    if not same_universe:
        print("NOTE: Universe metadata differs; this guardrail is being used as an explicit sentinel for canonical/selected divergence.")
        print(f"Run {args.run_a} source/hash: {metadata_a['universe_source']}/{metadata_a['raw_pool_returns_hash']}")
        print(f"Run {args.run_b} source/hash: {metadata_b['universe_source']}/{metadata_b['raw_pool_returns_hash']}")
        print("Skipping invariance check since universes are intentionally different.")
        return 0

    if diffs:
        print("FAIL: raw_pool_ew summaries drifted beyond tolerance.")
        print(json.dumps(diffs, indent=2))
        return 1

    print("PASS: raw_pool_ew summaries are invariant within tolerance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
