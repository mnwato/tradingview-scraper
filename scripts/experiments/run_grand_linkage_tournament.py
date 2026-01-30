import json
import logging
import os
import subprocess
from datetime import datetime

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("grand_linkage_tournament")


def run_experiment():
    linkages = ["single", "ward", "complete", "average"]
    # engines = ["custom", "skfolio", "pyportfolioopt", "cvxportfolio"]
    # profiles = ["hrp", "barbell", "min_variance"]
    # simulators = ["cvxportfolio"] # vectorbt is faster but cvxportfolio is high fidelity

    # We will use the default tournament settings from manifest,
    # but maybe restrict to save time if needed.
    # User asked for "tournament of portfolio engines, risk profiles, simulators matrix".
    # So we should ideally run the full set.

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_file = f"docs/reports/grand_linkage_tournament_{timestamp}.md"

    all_results = []

    # Find latest run for data source
    runs_dir = "artifacts/summaries/runs"
    runs = sorted([d for d in os.listdir(runs_dir) if d.startswith("2026") and os.path.isdir(os.path.join(runs_dir, d))], reverse=True)
    if not runs:
        logger.error("No run directory found")
        return
    latest_run_id = runs[0]
    logger.info(f"Using Base Run ID: {latest_run_id}")

    for linkage in linkages:
        logger.info(f"\n>>> Running Grand Tournament for HRP Linkage: {linkage}")

        env = os.environ.copy()
        env["TV_HRP_LINKAGE"] = linkage
        env["TV_RUN_ID"] = latest_run_id  # Reuse the run ID to use its data?
        # CAREFUL: If we reuse RUN_ID, backtest_engine might overwrite the main tournament_results.json
        # We should probably NOT set TV_RUN_ID, let it create a new one, OR assume backtest_engine doesn't overwrite?
        # backtest_engine writes to settings.run_data_dir.
        # If we use the same RUN_ID, it WILL overwrite.
        # But we want to use the *data* from the latest run.
        # backtest_engine loads returns from `BacktestEngine.returns` which comes from...
        # Wait, BacktestEngine.__init__ loads `data/lakehouse/portfolio_returns.pkl`.
        # This file is global (latest).
        # So we don't need to force TV_RUN_ID to read the data.
        # We can let it create a new run ID for the results.

        if "TV_RUN_ID" in env:
            del env["TV_RUN_ID"]

        cmd = [
            "uv",
            "run",
            "scripts/backtest_engine.py",
            "--tournament",
            # Run full matrix defined in manifest or defaults
            # But let's be explicit to ensure we cover HRP
            "--profiles",
            "hrp,barbell,min_variance,equal_weight,benchmark",
            "--engines",
            "custom,skfolio,pyportfolioopt,cvxportfolio",
            "--simulators",
            "cvxportfolio",
        ]

        try:
            # Run tournament
            # Capture stdout to find the new run ID or output path?
            # backtest_engine.py doesn't print the run ID at the end explicitly.
            # But it creates a directory in artifacts/summaries/runs/

            # We can detect the newest directory created.
            before_runs = set(os.listdir(runs_dir))

            subprocess.run(cmd, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            after_runs = set(os.listdir(runs_dir))
            new_runs = after_runs - before_runs

            if not new_runs:
                # Maybe it reused a run or didn't create one?
                # Or maybe it updated "latest"?
                # Let's find the absolute newest directory.
                current_runs = sorted([d for d in os.listdir(runs_dir) if d.startswith("2026")], reverse=True)
                target_run = current_runs[0]
            else:
                target_run = list(new_runs)[0]

            logger.info(f"Tournament Artifacts in: {target_run}")

            res_path = f"artifacts/summaries/runs/{target_run}/data/tournament_results.json"

            if os.path.exists(res_path):
                with open(res_path, "r") as f:
                    data = json.load(f)
                    # Parse full matrix
                    # Structure: results[simulator][engine][profile]["summary"]["sharpe"]
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

                                    all_results.append({"Linkage": linkage, "Simulator": sim, "Engine": eng, "Profile": prof, "Sharpe": sharpe, "Vol": vol, "Return": ret, "RunID": target_run})
            else:
                logger.error(f"Results not found for {linkage} in {target_run}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Tournament failed for {linkage}: {e.stdout.decode()}")

    # Save Report
    df = pd.DataFrame(all_results)
    if not df.empty:
        # Sort by Sharpe Descending
        df = df.sort_values("Sharpe", ascending=False)

        markdown = f"# Grand Linkage Tournament Report\nGenerated: {datetime.now()}\n\n"
        markdown += "## Top Performers\n"
        markdown += df.head(20).to_markdown(index=False)
        markdown += "\n\n## HRP Sensitivity Analysis\n"

        # HRP Specific Pivot
        hrp_df = df[df["Profile"] == "hrp"]
        if not hrp_df.empty:
            pivot = hrp_df.pivot_table(index=["Engine", "Simulator"], columns="Linkage", values="Sharpe")
            markdown += pivot.to_markdown()

        with open(report_file, "w") as f:
            f.write(markdown)

        logger.info(f"Report saved to {report_file}")
        print(markdown)
    else:
        logger.error("No results collected.")


if __name__ == "__main__":
    run_experiment()
