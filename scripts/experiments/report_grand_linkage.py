import json
import logging
import os
from datetime import datetime

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("report_grand_linkage")

RUN_MAP = {"single": "20260109-193211", "ward": "20260109-193249", "complete": "20260109-193326", "average": "20260109-193406"}


def generate_report():
    all_results = []

    for linkage, run_id in RUN_MAP.items():
        res_path = f"artifacts/summaries/runs/{run_id}/data/tournament_results.json"
        if not os.path.exists(res_path):
            logger.warning(f"Results missing for {linkage} ({run_id})")
            continue

        with open(res_path, "r") as f:
            data = json.load(f)
            results = data.get("results", {})
            for sim, engines_dict in results.items():
                for eng, profiles_dict in engines_dict.items():
                    for prof, details in profiles_dict.items():
                        if not isinstance(details, dict):
                            continue
                        summary = details.get("summary")
                        if summary:
                            sharpe = summary.get("sharpe")
                            vol = summary.get("annualized_vol")
                            ret = summary.get("annualized_return")

                            all_results.append({"Linkage": linkage, "Simulator": sim, "Engine": eng, "Profile": prof, "Sharpe": sharpe, "Vol": vol, "Return": ret, "RunID": run_id})

    df = pd.DataFrame(all_results)
    if df.empty:
        logger.error("No data collected")
        return

    # Filter for HRP to compare sensitivity
    hrp_df = df[df["Profile"] == "hrp"]

    # Filter for PyPortfolioOpt HRP specifically (as that's what we tuned)
    pypfopt_hrp = hrp_df[hrp_df["Engine"] == "pyportfolioopt"]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_file = f"docs/reports/grand_linkage_tournament_{timestamp}.md"

    with open(report_file, "w") as f:
        f.write(f"# Grand Linkage Tournament Report\nGenerated: {datetime.now()}\n\n")

        f.write("## PyPortfolioOpt HRP Sensitivity (Target)\n")
        if not pypfopt_hrp.empty:
            pivot = pypfopt_hrp.pivot_table(index=["Simulator"], columns="Linkage", values="Sharpe")
            f.write(pivot.to_markdown())
            f.write("\n\n")

        f.write("## Full HRP Landscape\n")
        pivot_all = hrp_df.pivot_table(index=["Engine", "Simulator"], columns="Linkage", values="Sharpe")
        f.write(pivot_all.to_markdown())
        f.write("\n\n")

        f.write("## Top 20 Performers (All Configurations)\n")
        f.write(df.sort_values("Sharpe", ascending=False).head(20).to_markdown(index=False))

    logger.info(f"Report saved to {report_file}")
    print(open(report_file).read())


if __name__ == "__main__":
    generate_report()
