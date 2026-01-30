import json
from pathlib import Path

import pandas as pd


def generate_audit():
    df = pd.read_csv("artifacts/summaries/calibration_results.csv")

    print("# 🛡️ Master Calibration Forensic Audit (v3.4.2)")

    # 1. Selection Alpha Analysis
    print("\n## 1. Selection Alpha Attribution")
    print("Quantifying the value added by v3.4 HTR filters vs a Selection-Naive baseline.")
    sel_stats = df.groupby("selection_mode").agg({"sharpe": "mean", "ann_return": "mean", "max_dd": "mean", "vol": "mean"}).round(4)
    print(sel_stats.to_markdown())

    alpha_value = sel_stats.loc["v3.4", "sharpe"] - sel_stats.loc["baseline", "sharpe"]
    print(f"\n**Total Selection Alpha (Sharpe Δ)**: {alpha_value:.4f}")

    # 2. Portfolio Engine Performance Matrix (v3.4 Standard)
    print("\n## 2. Portfolio Engine Risk Matrix (v3.4 Pool)")
    v34 = df[df["selection_mode"] == "v3.4"]
    matrix = v34.pivot_table(index="profile", columns="engine", values="sharpe", aggfunc="mean").round(4)
    print(matrix.to_markdown())

    # 3. Regime Shift Handling Audit
    print("\n## 3. Regime Shift & Adaptive Response")

    # Load regime shifts
    regimes = []
    regime_path = Path("artifacts/summaries/runs/final_calibration_v3.4/regime_audit.jsonl")
    if regime_path.exists():
        with open(regime_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    regimes.append({"ts": entry["timestamp"], "regime": entry["regime"], "score": entry["score"]})
                except Exception:
                    continue

    reg_df = pd.DataFrame(regimes)
    print("\n### Detected Regimes (Tournament Trace):")
    if not reg_df.empty:
        # Group by unique consecutive regimes
        reg_df["change"] = reg_df["regime"] != reg_df["regime"].shift()
        shifts = reg_df[reg_df["change"]].copy()
        print(shifts[["ts", "regime", "score"]].to_markdown(index=False))

    print("\n### Adaptive Engine Profile Selection:")
    adapt = v34[v34["engine"] == "adaptive"]
    if not adapt.empty:
        # We need to peek into the audit.jsonl for the 'adaptive_target' metadata
        # for a more granular view, but here we just show overall performance.
        print(adapt.groupby("profile").agg({"sharpe": "mean", "ann_return": "mean"}).round(4).to_markdown())


if __name__ == "__main__":
    generate_audit()
