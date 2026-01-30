import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from tradingview_scraper.settings import get_settings


def _load_results(run_id: str, runs_root: Path) -> Dict[str, Any]:
    run_path = runs_root / run_id / "tournament_results.json"
    if not run_path.exists():
        raise FileNotFoundError(f"tournament_results.json not found for run {run_id}: {run_path}")
    with run_path.open("r") as f:
        return json.load(f)


def _count_windows(node: Dict[str, Any]) -> int:
    windows = node.get("windows") or []
    return len(windows)


def _find_profiles(results: Dict[str, Any], profile_names: List[str]) -> List[Tuple[str, str, str, int]]:
    matches: List[Tuple[str, str, str, int]] = []
    for sim_name, engines in results.items():
        if not isinstance(engines, dict):
            continue
        for engine_name, profiles in engines.items():
            if not isinstance(profiles, dict):
                continue
            for profile_name in profile_names:
                if profile_name in profiles:
                    matches.append((sim_name, engine_name, profile_name, _count_windows(profiles[profile_name])))
    return matches


def _has_valid_windows(matches: List[Tuple[str, str, str, int]]) -> bool:
    return any(count > 0 for _, _, _, count in matches)


def _print_matches(label: str, matches: List[Tuple[str, str, str, int]]) -> None:
    if not matches:
        print(f"{label}: MISSING")
        return
    rows = ", ".join([f"{sim}/{engine}/{profile}={count}" for sim, engine, profile, count in matches])
    print(f"{label}: {rows}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit baseline availability in tournament results.")
    parser.add_argument("--run-id", default=os.getenv("TV_RUN_ID") or os.getenv("RUN_ID"))
    parser.add_argument("--runs-root", default=None)
    parser.add_argument("--strict", action="store_true", help="Fail if baseline availability is missing.")
    parser.add_argument("--require-raw-pool", action="store_true", help="Fail if raw_pool_ew windows are missing.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    args = parser.parse_args()

    if not args.run_id:
        print("Missing --run-id (or TV_RUN_ID/RUN_ID).", file=sys.stderr)
        return 2

    settings = get_settings()
    runs_root = Path(args.runs_root) if args.runs_root else settings.summaries_runs_dir
    data = _load_results(args.run_id, runs_root)
    results = data.get("results", {})

    market_matches = _find_profiles(results, ["market"])
    benchmark_matches = _find_profiles(results, ["benchmark"])
    raw_pool_matches = _find_profiles(results, ["raw_pool_ew"])

    summary = {
        "run_id": args.run_id,
        "market": market_matches,
        "benchmark": benchmark_matches,
        "raw_pool_ew": raw_pool_matches,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        _print_matches("market", market_matches)
        _print_matches("benchmark", benchmark_matches)
        _print_matches("raw_pool_ew", raw_pool_matches)

    failed = False
    if args.strict:
        if not _has_valid_windows(market_matches):
            failed = True
        if not _has_valid_windows(benchmark_matches):
            failed = True
        if args.require_raw_pool and not _has_valid_windows(raw_pool_matches):
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
