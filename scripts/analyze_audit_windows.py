import argparse
import json
import os
from typing import Any, Dict

import pandas as pd


def analyze(log_path: str, target_profile: str = "hrp"):
    if not os.path.exists(log_path):
        print(f"Log path not found: {log_path}")
        return

    # Data structures to hold per-window info
    # window_index -> { 'metrics': {}, 'weights': {} }
    windows: Dict[int, Dict[str, Any]] = {}

    with open(log_path, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("status") != "success":
                    continue

                step = entry.get("step")
                ctx = entry.get("context", {})
                profile = ctx.get("profile")

                if profile != target_profile:
                    continue

                w_idx = ctx.get("window_index")
                if w_idx is None:
                    continue

                if w_idx not in windows:
                    windows[w_idx] = {}

                outcome = entry.get("outcome", {})

                if step == "backtest_optimize":
                    # Extract Weights
                    metrics = outcome.get("metrics", {})
                    windows[w_idx]["weights"] = metrics.get("weights", {})

                elif step == "backtest_simulate":
                    # Extract Performance Metrics
                    metrics = outcome.get("metrics", {})
                    windows[w_idx]["perf"] = metrics

            except Exception:
                continue

    # Build DataFrame
    rows = []
    for w_idx, data in sorted(windows.items()):
        perf = data.get("perf", {})
        weights = data.get("weights", {})

        # Get Top 3 Assets by Weight
        sorted_weights = sorted(weights.items(), key=lambda x: abs(x[1]), reverse=True)
        top_assets = ", ".join([f"{k.split(':')[-1]}({v:.0%})" for k, v in sorted_weights[:3]])

        rows.append(
            {
                "Window": w_idx,
                "Sharpe": perf.get("sharpe", 0.0),
                "CAGR": perf.get("annualized_return", 0.0),
                "Vol": perf.get("annualized_vol", 0.0),
                "MaxDD": perf.get("max_drawdown", 0.0),
                "Turnover": perf.get("turnover", 0.0),
                "Top_Allocations": top_assets,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        print(f"No data found for profile: {target_profile}")
        return

    # Formatting
    # df["CAGR"] = df["CAGR"].map(lambda x: f"{x:.2f}%") # Keep as float for now if we want to sort/agg

    print(f"## Deep Window Audit: {target_profile}")
    print(df.to_markdown(index=False, floatfmt=".4f"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-path", required=True, help="Path to audit.jsonl")
    parser.add_argument("--profile", default="hrp", help="Target risk profile (default: hrp)")
    args = parser.parse_args()

    analyze(args.log_path, args.profile)
