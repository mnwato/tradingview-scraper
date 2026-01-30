import json
import sys

import pandas as pd


def print_table(results_path):
    try:
        with open(results_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {results_path}")
        return

    # Handle the "results_4d" wrapper if present
    results = data.get("results_4d", data)

    records = []
    # Structure: Mode -> Simulator -> Engine -> Profile -> Metrics
    for mode, mode_data in results.items():
        if not isinstance(mode_data, dict):
            continue

        for sim, sim_data in mode_data.items():
            if not isinstance(sim_data, dict):
                continue

            for engine, engine_data in sim_data.items():
                if not isinstance(engine_data, dict):
                    continue

                for profile, metrics in engine_data.items():
                    if not isinstance(metrics, dict):
                        continue

                    # Check if metrics are directly here or nested
                    # Based on previous output, "windows" is here. Metrics should be too.

                    records.append(
                        {
                            "Sel": mode,
                            "Sim": sim,
                            "Eng": engine,
                            "Prof": profile,
                            "Ret": metrics.get("annualized_return", 0.0),
                            "Vol": metrics.get("annualized_volatility", 0.0),
                            "Sharpe": metrics.get("sharpe_ratio", 0.0),
                            "MaxDD": metrics.get("max_drawdown", 0.0),
                        }
                    )

    if not records:
        print("No records found in the results.")
        return

    df = pd.DataFrame(records)

    # Sort for readability: Selection -> Simulator -> Engine -> Profile
    df = df.sort_values(by=["Sel", "Sim", "Eng", "Prof"])

    # Format
    df["Ret"] = df["Ret"].apply(lambda x: f"{x:.2%}")
    df["Vol"] = df["Vol"].apply(lambda x: f"{x:.2%}")
    df["MaxDD"] = df["MaxDD"].apply(lambda x: f"{x:.2%}")
    df["Sharpe"] = df["Sharpe"].apply(lambda x: f"{x:.2f}")

    print(df.to_markdown(index=False, tablefmt="github"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        import glob
        import os

        runs = sorted(glob.glob("artifacts/summaries/runs/*"), key=os.path.getmtime, reverse=True)
        if runs:
            latest_run = runs[0]
            results_path = os.path.join(latest_run, "tournament_4d_results.json")
            print(f"Auto-detected latest run: {results_path}\n")
            print_table(results_path)
        else:
            print("No runs found.")
    else:
        print_table(sys.argv[1])
