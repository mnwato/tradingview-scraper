import json
from pathlib import Path

import pandas as pd


def generate_risk_report():
    path = Path("artifacts/summaries/latest/tournament_4d_results.json")
    if not path.exists():
        print("Results not found.")
        return

    with open(path, "r") as f:
        data = json.load(f)

    results_4d = data.get("results_4d", {})
    rows = []

    # Structure: results_4d[selection_mode][simulator][engine][profile] -> {summary, ...}

    for mode, sim_data in results_4d.items():
        for sim, engines in sim_data.items():
            for eng, profiles in engines.items():
                for prof, res in profiles.items():
                    if not res or "summary" not in res:
                        continue

                    summ = res["summary"]
                    rows.append(
                        {
                            "Selection": mode,
                            "Simulator": sim,
                            "Engine": eng,
                            "Profile": prof,
                            "Return": summ.get("total_return", 0),
                            "Volatility": summ.get("annual_volatility", 0),
                            "MaxDD": summ.get("max_drawdown", 0),
                            "Sharpe": summ.get("sharpe", 0),
                            "Calmar": summ.get("calmar", 0),
                        }
                    )

    if not rows:
        print("No results found.")
        return

    df = pd.DataFrame(rows)

    # Aggregation: Group by Profile and Engine (averaging across simulators/selections)
    # to see Engine Bias and Profile Characteristics.
    # Actually, let's look at specific slices.

    # 1. Risk Profile Characteristics (Averaged across everything else)
    print("\n--- Risk Profile Performance (Avg) ---")
    prof_stats = df.groupby("Profile")[["Return", "Volatility", "MaxDD", "Sharpe"]].mean().sort_values("Volatility")
    print(prof_stats.to_markdown())

    # 2. Engine Fidelity (Risk Parity Only)
    print("\n--- Risk Parity Engine Comparison ---")
    rp_df = df[df["Profile"] == "risk_parity"].groupby("Engine")[["Return", "Volatility", "MaxDD", "Sharpe"]].mean()
    print(rp_df.to_markdown())

    # 3. HRP Engine Comparison
    print("\n--- HRP Engine Comparison ---")
    hrp_df = df[df["Profile"] == "hrp"].groupby("Engine")[["Return", "Volatility", "MaxDD", "Sharpe"]].mean()
    print(hrp_df.to_markdown())

    # 4. Selection Impact (v2 vs v3.1)
    print("\n--- Selection Mode Impact ---")
    sel_df = df.groupby("Selection")[["Return", "Volatility", "MaxDD", "Sharpe"]].mean()
    print(sel_df.to_markdown())

    # Save detailed report
    out_path = Path("artifacts/summaries/latest/risk_profile_report.md")
    with open(out_path, "w") as f:
        f.write("# Risk Profile & Engine Fidelity Report\n\n")

        f.write("## 1. Risk Profile Characteristics\n")
        f.write("Averaged across all engines and selections. Lower volatility expected for RP/HRP.\n\n")
        f.write(prof_stats.to_markdown())
        f.write("\n\n")

        f.write("## 2. Engine Fidelity: Risk Parity\n")
        f.write("Comparing engines for the `risk_parity` profile. CVXPortfolio and Custom should align.\n\n")
        f.write(rp_df.to_markdown())
        f.write("\n\n")

        f.write("## 3. Engine Fidelity: HRP\n")
        f.write("Comparing engines for the `hrp` profile.\n\n")
        f.write(hrp_df.to_markdown())
        f.write("\n\n")

        f.write("## 4. Selection Mode Impact\n")
        f.write("Comparing `v2` (Stable) vs `v3.1` (Alpha).\n\n")
        f.write(sel_df.to_markdown())

    print(f"\nReport saved to {out_path}")


if __name__ == "__main__":
    generate_risk_report()
