import json
import os
import sys
from pathlib import Path

import pandas as pd


def generate():
    # Support rebalance audit results specifically
    if "--rebalance" in sys.argv:
        path = Path("artifacts/summaries/latest/rebalance_audit_results.json")
    else:
        run_id = os.getenv("TV_RUN_ID")
        if run_id:
            path = Path(f"artifacts/summaries/runs/{run_id}/tournament_4d_results.json")
        else:
            path = Path("artifacts/summaries/latest/tournament_4d_results.json")

    if not path.exists():
        # Try finding the latest run directory if no TV_RUN_ID
        runs_dir = Path("artifacts/summaries/runs")
        if runs_dir.exists():
            # Get all subdirectories, excluding 'latest'
            subdirs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name != "latest"]
            # Sort by modification time
            runs = sorted(subdirs, key=lambda x: x.stat().st_mtime, reverse=True)
            if runs:
                fn = "rebalance_audit_results.json" if "--rebalance" in sys.argv else "tournament_4d_results.json"
                path = runs[0] / fn

    if not path.exists():
        print(f"Results not found at {path}")
        return

    with open(path, "r") as f:
        data = json.load(f)

    rows = []

    # Check if it's rebalance audit format or standard 4d
    if "rebalance_audit_results" in data:
        results = data["rebalance_audit_results"]
        # dimensions: [rebalance_mode][selection_mode][simulator][engine][profile]
        for reb_mode, sel_data in results.items():
            for sel_mode, sim_data in sel_data.items():
                for sim, eng_data in sim_data.items():
                    for eng, prof_data in eng_data.items():
                        for prof, res in prof_data.items():
                            if not res or "summary" not in res or res["summary"] is None:
                                continue
                            summary = res["summary"]
                            rows.append(
                                {
                                    "Rebalance": str(reb_mode),
                                    "Mode": str(sel_mode),
                                    "Simulator": str(sim),
                                    "Engine": str(eng),
                                    "Profile": str(prof),
                                    "Return (%)": f"{summary.get('annualized_return', summary.get('total_cumulative_return', 0)) * 100:.2f}%",
                                    "Sharpe": round(float(summary.get("avg_window_sharpe", 0)), 2),
                                    "Vol (%)": f"{summary.get('annualized_vol', 0) * 100:.2f}%",
                                    "MDD (%)": f"{summary.get('max_drawdown', 0) * 100:.2f}%",
                                    "Turnover (%)": f"{summary.get('avg_turnover', 0) * 100:.2f}%",
                                }
                            )
    else:
        results_4d = data.get("results_4d", {})
        for mode, res_3d in results_4d.items():
            for sim, engines in res_3d.items():
                if not isinstance(engines, dict):
                    continue
                for eng, profiles in engines.items():
                    if not isinstance(profiles, dict):
                        continue
                    for prof, p_data in profiles.items():
                        if prof == "_status" or p_data is None or "summary" not in p_data or p_data["summary"] is None:
                            continue

                        summary = p_data["summary"]
                        rows.append(
                            {
                                "Mode": str(mode),
                                "Simulator": str(sim),
                                "Engine": str(eng),
                                "Profile": str(prof),
                                "Return (%)": f"{summary.get('annualized_return', 0) * 100:.2f}%",
                                "Sharpe": round(float(summary.get("avg_window_sharpe", 0)), 2),
                                "Vol (%)": f"{summary.get('annualized_vol', 0) * 100:.2f}%",
                                "MDD (%)": f"{summary.get('max_drawdown', 0) * 100:.2f}%",
                                "Turnover (%)": f"{summary.get('avg_turnover', 0) * 100:.2f}%",
                            }
                        )

    if not rows:
        print("No results to display.")
        return

    df = pd.DataFrame(rows)
    df = df.sort_values("Sharpe", ascending=False)

    period = str(data.get("meta", {}).get("period", "N/A"))
    markdown_table = str(df.to_markdown(index=False))

    output_path = path.parent / ("full_rebalance_comparison_table.md" if "rebalance_audit_results" in data else "full_4d_comparison_table.md")
    with open(output_path, "w") as f:
        f.write(f"# 📋 {'Rebalance Audit' if 'rebalance_audit_results' in data else 'Full 4D Tournament'} Comparison\n\n")
        f.write(f"**Period:** {period}\n")
        f.write(f"**Total Combinations:** {len(df)}\n\n")
        f.write(markdown_table)
        f.write("\n")

    print(f"✅ Comparison table generated at: {output_path}")
    print("\n" + markdown_table)

    # Print rebalance summary if flag present
    if "--print-rebalance-summary" in sys.argv:
        print("\n--- REBALANCE MODE SUMMARY ---")
        # Ensure Return and Turnover are floats for averaging
        df_summary = pd.DataFrame(rows)

        # Helper to convert "12.34%" strings back to floats
        def pct_to_float(s):
            try:
                return float(s.strip("%")) / 100.0
            except Exception:
                return 0.0

        df_summary["Ret_Val"] = df_summary["Return (%)"].apply(pct_to_float)
        df_summary["TO_Val"] = df_summary["Turnover (%)"].apply(pct_to_float)

        reb_grp = df_summary.groupby("Rebalance").agg({"Sharpe": "mean", "Ret_Val": "mean", "TO_Val": "mean"}).sort_values("Sharpe", ascending=False)

        reb_grp.columns = ["Avg Sharpe", "Avg Return", "Avg Turnover"]
        print(reb_grp.to_markdown())


if __name__ == "__main__":
    generate()
