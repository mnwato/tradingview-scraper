import json
from pathlib import Path

import numpy as np
import pandas as pd


def audit_engine_stability():
    results_path = "artifacts/summaries/runs/20260101-002201/tournament_results.json"
    if not Path(results_path).exists():
        print("Results file not found.")
        return

    with open(results_path, "r") as f:
        data = json.load(f)

    # We'll focus on 'custom' simulator for engine comparison
    sim = "custom"
    engines = ["custom", "skfolio"]
    profiles = ["min_variance", "max_sharpe"]

    summary = []

    for prof in profiles:
        c_windows = data["results"][sim]["custom"].get(prof, {}).get("windows", [])
        s_windows = data["results"][sim]["skfolio"].get(prof, {}).get("windows", [])

        # Match windows by start_date
        c_map = {w["start_date"]: w for w in c_windows}
        s_map = {w["start_date"]: w for w in s_windows}

        common_dates = sorted(set(c_map.keys()) & set(s_map.keys()))

        for d in common_dates:
            cw = c_map[d]
            sw = s_map[d]

            # Outlier check: Deviation from mean
            # Here we just calculate the difference
            diff_sharpe = sw["sharpe"] - cw["sharpe"]
            diff_vol = sw["vol"] - cw["vol"]

            # Kappa check - the existing results might NOT have kappa yet
            # as I just added it to the script but haven't run a successful 2025 matrix with it.
            # I will check if 'kappa' key exists.
            kappa = sw.get("kappa", cw.get("kappa", 1.0))

            summary.append(
                {
                    "profile": prof,
                    "date": d,
                    "regime": cw["regime"],
                    "custom_sharpe": cw["sharpe"],
                    "skfolio_sharpe": sw["sharpe"],
                    "diff_sharpe": diff_sharpe,
                    "custom_vol": cw["vol"],
                    "skfolio_vol": sw["vol"],
                    "diff_vol": diff_vol,
                    "kappa": kappa,
                }
            )

    df = pd.DataFrame(summary)
    if df.empty:
        print("No overlapping windows found.")
        return

    print("--- Engine Stability Audit (skfolio vs custom) ---")
    for prof in profiles:
        pdf = df[df["profile"] == prof]
        print(f"\nProfile: {prof}")
        print(f"Avg Sharpe Diff (skfolio - custom): {pdf['diff_sharpe'].mean():.4f}")
        print(f"Avg Vol Diff: {pdf['diff_vol'].mean():.6f}")

        # Identify Outliers (> 2 sigma)
        mean_diff = pdf["diff_sharpe"].mean()
        std_diff = pdf["diff_sharpe"].std()
        outliers = pdf[np.abs(pdf["diff_sharpe"] - mean_diff) > 2 * std_diff]

        print(f"Outlier Windows (>2σ): {len(outliers)}")
        for _, row in outliers.iterrows():
            print(f"- {row['date']} ({row['regime']}): Sharpe Diff={row['diff_sharpe']:.4f}")


if __name__ == "__main__":
    audit_engine_stability()
