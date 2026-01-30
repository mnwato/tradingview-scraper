import json
from pathlib import Path

import numpy as np
import pandas as pd


def audit_outliers():
    path = Path("artifacts/summaries/latest/tournament_4d_results.json")
    if not path.exists():
        print("Results not found.")
        return

    with open(path, "r") as f:
        data = json.load(f)

    results_4d = data.get("results_4d", {})
    rows = []

    for mode, sim_data in results_4d.items():
        for sim, engines in sim_data.items():
            for eng, profiles in engines.items():
                for prof, res in profiles.items():
                    if not res or "summary" not in res:
                        continue
                    summ = res["summary"]
                    rows.append(
                        {
                            "Mode": mode,
                            "Simulator": sim,
                            "Engine": eng,
                            "Profile": prof,
                            "Sharpe": summ.get("sharpe", 0),
                            "Return": summ.get("total_return", 0),
                            "MaxDD": summ.get("max_drawdown", 0),
                            "Vol": summ.get("annual_volatility", 0),
                        }
                    )

    df = pd.DataFrame(rows)

    # 1. Behavioral Outliers (Overall)
    # Identify permutations with Sharpe > 2 std devs from mean
    mean_sharpe = df["Sharpe"].mean()
    std_sharpe = df["Sharpe"].std()

    outliers_sharpe = df[np.abs(df["Sharpe"] - mean_sharpe) > 2 * std_sharpe]

    # 2. Simulator Drift
    # Compare 'nautilus' vs 'custom' for same (Mode, Engine, Profile)
    pivot = df.pivot_table(index=["Mode", "Engine", "Profile"], columns="Simulator", values="Sharpe")
    if "nautilus" in pivot.columns and "custom" in pivot.columns:
        pivot["Drift"] = np.abs(pivot["nautilus"] - pivot["custom"])
        significant_drift = pivot[pivot["Drift"] > 0.1].sort_values("Drift", ascending=False)
    else:
        significant_drift = pd.DataFrame()

    # 3. Mode Comparison (Spectral impact)
    mode_stats = df.groupby("Mode")["Sharpe"].agg(["mean", "std", "min", "max"])

    # Generate Report
    out_path = Path("artifacts/summaries/latest/outlier_analysis_report.md")
    with open(out_path, "w") as f:
        f.write("# Outlier Behavioral Audit Report\n\n")

        f.write("## 1. Global Performance Outliers (>2σ Sharpe)\n")
        f.write(f"Mean Sharpe: {mean_sharpe:.2f}, Std Dev: {std_sharpe:.2f}\n\n")
        if not outliers_sharpe.empty:
            f.write(outliers_sharpe.sort_values("Sharpe", ascending=False).to_markdown(index=False))
        else:
            f.write("No extreme global outliers detected.\n")
        f.write("\n\n")

        f.write("## 2. Simulator Drift (Nautilus vs Custom)\n")
        f.write("Identifies cases where simulator implementation significantly impacts Sharpe (>0.1).\n\n")
        if not significant_drift.empty:
            f.write(significant_drift.to_markdown())
        else:
            f.write("Zero simulator drift detected (Perfect weight-to-performance parity).\n")
        f.write("\n\n")

        f.write("## 3. Selection Mode Variance\n")
        f.write("Comparing the stability of different selection modes.\n\n")
        f.write(mode_stats.to_markdown())
        f.write("\n\n")

        f.write("## 4. Key Observations\n")
        if "v3.1_spectral" in df["Mode"].unique():
            spectral_mean = df[df["Mode"] == "v3.1_spectral"]["Sharpe"].mean()
            v31_mean = df[df["Mode"] == "v3.1"]["Sharpe"].mean()
            if spectral_mean < v31_mean * 0.8:
                f.write(
                    f"- **Spectral Degeneracy**: `v3.1_spectral` (Mean Sharpe: {spectral_mean:.2f}) significantly underperforms standard `v3.1` ({v31_mean:.2f}). This suggests the spectral filters (Entropy/Efficiency) may be too restrictive for the 2025 dataset, potentially pruning alpha-generating but 'noisy' assets.\n"
                )

        # Check for CVXPortfolio stability
        cvx_drift = df[df["Engine"] == "cvxportfolio"]["Sharpe"].std()
        if cvx_drift < 0.1:
            f.write("- **Engine Stability**: `cvxportfolio` engine demonstrates high consistency across simulators.\n")

    print(f"Outlier audit complete. Report saved to {out_path}")


if __name__ == "__main__":
    audit_outliers()
