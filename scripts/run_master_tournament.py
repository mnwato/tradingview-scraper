import argparse
import datetime
import json
import logging
import os
import subprocess
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("calibration_tournament")


def run_backtest(selection_mode, run_id_prefix):
    run_id = f"{run_id_prefix}_{selection_mode}"
    logger.info(f">>> Running Tournament for Selection Mode: {selection_mode} (Run ID: {run_id})")

    cmd = ["uv", "run", "scripts/backtest_engine.py", "--train-window", "60", "--test-window", "40", "--step-size", "20", "--selection-mode", selection_mode]

    env = os.environ.copy()
    env["TV_RUN_ID"] = run_id

    try:
        subprocess.run(cmd, env=env, check=True)
        return run_id
    except subprocess.CalledProcessError as e:
        logger.error(f"Backtest failed for {selection_mode}: {e}")
        return None


def aggregate_results(run_ids):
    all_data = []
    for selection_mode, run_id in run_ids.items():
        if not run_id:
            continue
        audit_path = Path(f"artifacts/summaries/runs/{run_id}/audit.jsonl")
        if not audit_path.exists():
            logger.warning(f"Audit ledger not found: {audit_path}")
            continue

        with open(audit_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("step") == "backtest_simulate" and entry.get("status") == "success":
                        ctx = entry.get("context", {})
                        metrics = entry.get("outcome", {}).get("metrics", {})

                        all_data.append(
                            {
                                "selection_mode": selection_mode,
                                "window": ctx.get("window_index"),
                                "engine": ctx.get("engine"),
                                "profile": ctx.get("profile"),
                                "sharpe": metrics.get("sharpe", 0.0),
                                "ann_return": metrics.get("annualized_return", 0.0),
                                "max_dd": metrics.get("max_drawdown", 0.0),
                                "vol": metrics.get("annualized_vol", 0.0),
                            }
                        )
                except Exception:
                    continue

    return pd.DataFrame(all_data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id-prefix", default=f"calib_{datetime.datetime.now().strftime('%m%d_%H%M')}")
    args = parser.parse_args()

    selection_modes = ["baseline", "liquid_htr", "v3.2", "v3.4", "v4"]
    run_ids = {}

    for mode in selection_modes:
        run_ids[mode] = run_backtest(mode, args.run_id_prefix)

    df = aggregate_results(run_ids)
    if df.empty:
        logger.error("No results aggregated.")
        return

    # Save raw aggregation
    summary_path = Path("artifacts/summaries/calibration_results.csv")
    df.to_csv(summary_path, index=False)
    logger.info(f"Saved master calibration results to {summary_path}")

    # 1. Selection Alpha Analysis
    print("\n### 🧬 Selection Alpha Attribution (Avg Sharpe)")
    sel_pivot = df.groupby(["selection_mode"]).agg({"sharpe": "mean", "ann_return": "mean", "max_dd": "mean"})
    print(sel_pivot.to_markdown())

    # 2. Risk Profile Matrix (for HTR v3.4)
    print("\n### 📈 v3.4 HTR: Risk Profile Matrix (Avg Sharpe)")
    v34_df = df[df["selection_mode"] == "v3.4"]
    if not v34_df.empty:
        pivot_v34 = v34_df.pivot_table(index="profile", columns="engine", values="sharpe", aggfunc="mean")
        print(pivot_v34.to_markdown())

    # 3. Adaptive Engine Trace
    print("\n### 🧠 Adaptive Engine performance across regimes")
    adaptive_df = df[df["engine"] == "adaptive"]
    if not adaptive_df.empty:
        adapt_pivot = adaptive_df.groupby(["selection_mode", "profile"]).agg({"sharpe": "mean", "ann_return": "mean"})
        print(adapt_pivot.to_markdown())


if __name__ == "__main__":
    main()
