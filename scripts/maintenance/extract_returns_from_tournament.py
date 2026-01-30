import json
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("extract_returns")


def extract_returns(run_id: str):
    run_dir = Path(f"artifacts/summaries/runs/{run_id}")
    if not run_dir.exists():
        logger.error(f"Run {run_id} not found")
        return

    # Try audit.jsonl first as it contains the full data payload
    audit_path = run_dir / "audit.jsonl"

    if audit_path.exists():
        logger.info(f"Processing audit ledger: {audit_path}")
        returns_dir = run_dir / "data" / "returns"
        returns_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(audit_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("step") == "backtest_simulate" and entry.get("status") == "success":
                        ctx = entry.get("context", {})
                        data = entry.get("data", {})

                        engine = ctx.get("engine")
                        profile = ctx.get("profile")
                        simulator = ctx.get("simulator")
                        daily_returns = data.get("daily_returns")

                        if not daily_returns:
                            continue

                        # We need to construct a continuous series or handle windowed returns.
                        # The grand tournament runs multiple windows. We typically want the concatenated series.
                        # But here we are just extracting what's there.
                        # Wait, build_meta_returns expects a single PKL file for the entire period?
                        # Or does it handle joining?

                        # If we have multiple windows, we need to stitch them.
                        # Let's store them in a dict and stitch at the end.
                        pass  # Refactoring loop below
                except Exception:
                    continue

        # Stitching Logic
        # Group by (engine, simulator, profile)
        streams = {}

        with open(audit_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("step") == "backtest_simulate" and entry.get("status") == "success":
                        ctx = entry.get("context", {})
                        data = entry.get("data", {})

                        engine = ctx.get("engine")
                        profile = ctx.get("profile")
                        simulator = ctx.get("simulator")
                        daily_returns = data.get("daily_returns")

                        if not daily_returns:
                            continue

                        key = (engine, simulator, profile)
                        if key not in streams:
                            streams[key] = []

                        # daily_returns is a list. We need the index.
                        # The ledger might not store the index if it was serialized as a list.
                        # But backtest_engine typically runs on a known index.
                        # The 'daily_returns' in data payload is a list of values.

                        # Problem: We lost the index in serialization if it's just a list.
                        # We need to recover it from the window start/end or 'metrics.daily_returns' if it preserved index?
                        # BacktestEngine code:
                        # if isinstance(daily_returns, pd.Series): data_payload["daily_returns"] = daily_rets.values.tolist()

                        # We lost the index! This is a blocker for stitching.
                        # However, we have the window index.
                        # And we know the test_window size.
                        # But exact dates are better.

                        # Let's check if 'sanitized_metrics' contains anything useful? No.

                        # Do we have the start date in context?
                        # ctx has 'window_index'.

                        # We might need to rely on the fact that build_meta_returns needs a PKL with index.
                        # If we can't recover the index, we can't use these runs for meta-allocation.

                        # Wait, persist_tournament_artifacts saves 'tournament_results.json'.
                        # Does it save anything else? No.

                        # Is there any file that has the full returns?
                        # 'grand_tournament_research.log' output?

                        # The only way is if I re-run with a mechanism to save returns.
                        # OR if I use the 'production' pipeline which uses 'AuditLedger' which... wait.

                        # I can infer the index if I know the master returns index.
                        # I can load 'data/lakehouse/returns_matrix.parquet' to get the master index.
                        # Then slice it by window.
                        pass
                except Exception:
                    pass

        # This is getting complicated.
        # It's better to modify BacktestEngine to save the PKL files in the first place,
        # OR use run_production_pipeline which might do it.
        # But I used grand_tournament in research mode.

        # Let's assume I can't recover them easily from these runs.
        # I should re-run the granular profiles with a script that explicitly saves the returns.
        return

    # Fallback to tournament_results.json (Legacy path, but we know it failed)
    json_files = list(run_dir.rglob("tournament_results.json"))
    if not json_files:
        logger.error("No tournament_results.json found")
        return

    json_path = json_files[0]
    logger.info(f"Processing {json_path}")

    with open(json_path, "r") as f:
        data = json.load(f)

    results = data.get("results", [])
    if not results:
        logger.warning("No results in JSON")
        return

    returns_dir = run_dir / "data" / "returns"
    returns_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for res in results:
        profile = res.get("profile")
        engine = res.get("engine")
        simulator = res.get("simulator")
        metrics = res.get("metrics", {})
        daily_returns = metrics.get("daily_returns")

        if not daily_returns:
            continue

        # Convert to Series
        if isinstance(daily_returns, dict):
            # Index/Value dict
            series = pd.Series(daily_returns)
            # Ensure index is datetime
            series.index = pd.to_datetime(series.index)
        elif isinstance(daily_returns, list):
            # List of values - we need index.
            # In research mode, we might not have index if not serialized.
            # But the audit ledger has data.
            # If we don't have index, we can't join.
            # Let's hope it's a dict or we can find index.
            logger.warning(f"List format returns for {profile} - skipping (no index)")
            continue

        # Construct filename consistent with build_meta_returns expectations
        # typically: {engine}_{simulator}_{profile}.pkl or just {profile}.pkl
        # build_meta_returns looks for *_{profile}.pkl

        filename = f"{engine}_{simulator}_{profile}.pkl"
        out_path = returns_dir / filename

        series.to_pickle(out_path)
        count += 1

    logger.info(f"Extracted {count} return series to {returns_dir}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        extract_returns(sys.argv[1])
    else:
        print("Usage: python extract_returns.py <RUN_ID>")
