import json
from pathlib import Path

import pandas as pd


def generate_rebalance_table():
    path = Path("artifacts/summaries/latest/rebalance_audit_results.json")
    if not path.exists():
        print("Results not found.")
        return

    with open(path, "r") as f:
        data = json.load(f)

    results = data.get("rebalance_audit_results", {})
    rows = []

    # dimensions: [rebalance_mode][selection_mode][simulator][engine][profile]
    for reb_mode, sel_data in results.items():
        for sel_mode, sim_data in sel_data.items():
            for sim, eng_data in sim_data.items():
                for eng, prof_data in eng_data.items():
                    for prof, res in prof_data.items():
                        if not res or "summary" not in res or res["summary"] is None:
                            continue

                        summ = res["summary"]
                        rows.append(
                            {
                                "Rebalance": reb_mode,
                                "Selection": sel_mode,
                                "Simulator": sim,
                                "Engine": eng,
                                "Profile": prof,
                                "Return": summ.get("total_cumulative_return", 0),
                                "Sharpe": summ.get("avg_window_sharpe", 0),
                                "Vol": summ.get("annualized_vol", 0),
                                "MDD": summ.get("max_drawdown", 0),
                                "Turnover": summ.get("avg_turnover", 0),
                            }
                        )

    if not rows:
        print("No summary data found.")
        return

    df = pd.DataFrame(rows)

    # 1. Main Efficiency Rank (Sorted by Net Sharpe)
    # Group by Rebalance Mode
    print("\n--- Rebalance Mode Efficiency ---")
    reb_stats = df.groupby("Rebalance")[["Return", "Sharpe", "Vol", "MDD", "Turnover"]].mean().sort_values("Sharpe", ascending=False)
    print(reb_stats.to_markdown())

    # 2. Churn Penalty Audit
    # Compare 'window' vs 'daily' for same (Selection, Engine, Profile, Simulator)
    # We focus on the cost-aware ones (cvxportfolio simulator)
    pivot_ret = df[df["Simulator"] == "cvxportfolio"].pivot_table(index=["Selection", "Engine", "Profile"], columns="Rebalance", values="Return")
    if "window" in pivot_ret.columns and "daily" in pivot_ret.columns:
        pivot_ret["Churn_Penalty"] = pivot_ret["daily"] - pivot_ret["window"]
        churn_audit = pivot_ret.sort_values("Churn_Penalty", ascending=False)
    else:
        churn_audit = pd.DataFrame()

    # 3. Frequency Optimization (Quarterly would need another run, currently comparing Window vs Daily)

    # Save Reports
    out_dir = path.parent

    # Efficiency Rank MD
    with open(out_dir / "rebalance_efficiency_rank.md", "w") as f:
        f.write("# Rebalance Efficiency Rank\n\n")
        f.write("Averaged across all selection modes, engines, and profiles.\n\n")
        f.write(reb_stats.to_markdown())
        f.write("\n")

    # Churn Audit MD
    with open(out_dir / "churn_penalty_audit.md", "w") as f:
        f.write("# Churn Penalty Audit\n\n")
        f.write("Comparing Daily vs Window rebalancing. Positive Churn Penalty means Daily return > Window return.\n\n")
        if not churn_audit.empty:
            f.write(churn_audit.to_markdown())
        else:
            f.write("Insufficient data for churn audit.\n")

    print(f"Rebalance reports generated in {out_dir}")


if __name__ == "__main__":
    generate_rebalance_table()
