import argparse
import json
from pathlib import Path

import pandas as pd


def compare_alpha(baseline_run, target_run):
    b_path = Path(f"artifacts/summaries/runs/{baseline_run}/audit.jsonl")
    t_path = Path(f"artifacts/summaries/runs/{target_run}/audit.jsonl")

    if not b_path.exists() or not t_path.exists():
        print("One or both runs not found.")
        return

    def load_metrics(path):
        data = []
        with open(path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("step") == "backtest_simulate" and entry.get("status") == "success":
                        ctx = entry.get("context", {})
                        m = entry.get("outcome", {}).get("metrics", {})
                        data.append(
                            {"window": ctx.get("window_index"), "engine": ctx.get("engine"), "profile": ctx.get("profile"), "sharpe": m.get("sharpe", 0.0), "return": m.get("annualized_return", 0.0)}
                        )
                except Exception:
                    continue
        return pd.DataFrame(data)

    df_b = load_metrics(b_path)
    df_t = load_metrics(t_path)

    if df_b.empty or df_t.empty:
        print("No metrics found in one or both runs.")
        return

    # Merge on window, engine, profile
    merged = pd.merge(df_b, df_t, on=["window", "engine", "profile"], suffixes=("_base", "_target"))
    merged["sharpe_diff"] = merged["sharpe_target"] - merged["sharpe_base"]

    print(f"# 🧬 Selection Alpha Comparison: {target_run} vs {baseline_run}")

    # 1. Overall Aggregation
    summary = merged.groupby(["engine", "profile"]).agg({"sharpe_base": "mean", "sharpe_target": "mean", "sharpe_diff": "mean"}).round(4)

    print("\n## 1. Average Selection Alpha (Sharpe Δ) by Portfolio Configuration")
    print(summary.to_markdown())

    # 2. Top Added Value Windows
    print("\n## 2. Top Alpha Windows (Where Selection Filter Added Most Value)")
    top_windows = merged.sort_values("sharpe_diff", ascending=False).head(10)
    print(top_windows[["window", "engine", "profile", "sharpe_base", "sharpe_target", "sharpe_diff"]].to_markdown(index=False))

    # 3. Alpha Decay Analysis (Negative Diff)
    print("\n## 3. Density Drag (Where Selection Filtering Cost Performance)")
    drag_windows = merged.sort_values("sharpe_diff", ascending=True).head(5)
    print(drag_windows[["window", "engine", "profile", "sharpe_base", "sharpe_target", "sharpe_diff"]].to_markdown(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    compare_alpha(args.baseline, args.target)
