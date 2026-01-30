import json
import logging
import os
import subprocess

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("linkage_tournament")


def run_experiment():
    linkages = ["single", "ward", "complete", "average"]
    results = []

    for linkage in linkages:
        logger.info(f"\n>>> Running Tournament for HRP Linkage: {linkage}")

        # Set environment variable
        env = os.environ.copy()
        env["TV_HRP_LINKAGE"] = linkage

        # Run backtest engine restricted to pyportfolioopt:hrp
        cmd = ["uv", "run", "scripts/backtest_engine.py", "--tournament", "--engines", "pyportfolioopt", "--profiles", "hrp", "--simulators", "cvxportfolio"]

        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)

            # Find the latest run directory
            runs_dir = "artifacts/summaries/runs"
            runs = sorted([d for d in os.listdir(runs_dir) if d.startswith("2026") and os.path.isdir(os.path.join(runs_dir, d))], reverse=True)

            if not runs:
                logger.error("No run directory found")
                continue

            latest_run_dir = os.path.join(runs_dir, runs[0])
            res_path = os.path.join(latest_run_dir, "data", "tournament_results.json")
            # Or usually it's in reports/backtest or just in the data dir?
            # Based on persist_tournament_artifacts, it's run_data_dir which usually maps to runs/ID/data or similar.
            # But let's check standard layout.
            # settings.run_data_dir usually artifacts/summaries/runs/ID/data

            # Check a few locations
            possible_paths = [
                os.path.join(latest_run_dir, "data", "tournament_results.json"),
                os.path.join(latest_run_dir, "tournament_results.json"),
                os.path.join(latest_run_dir, "reports", "backtest", "tournament_results.json"),
            ]

            found_file = False
            for p in possible_paths:
                if os.path.exists(p):
                    res_path = p
                    found_file = True
                    break

            if found_file:
                with open(res_path, "r") as f:
                    data = json.load(f)
                    try:
                        windows = data["results"]["cvxportfolio"]["pyportfolioopt"]["hrp"]["windows"]
                        # Find Window 6 (start_date roughly 2025-09-29)
                        # Or just take the last window?
                        # Window index isn't explicitly in the window dict usually, just order.
                        # But let's check the date.
                        target_start = "2025-09-29"

                        w6_sharpe = None
                        if linkage == linkages[0]:
                            logger.info(f"Available Windows: {[w.get('start_date') for w in windows]}")

                        for w in windows:
                            # Let's just grab the LAST window, which is likely Window 6
                            # Or based on previous log: 2025-09-29
                            if "2025-09" in w.get("start_date", ""):
                                w6_sharpe = w.get("sharpe")
                                break

                        if w6_sharpe is None and windows:
                            w6_sharpe = windows[-1].get("sharpe")  # Fallback to last

                        summary = data["results"]["cvxportfolio"]["pyportfolioopt"]["hrp"]["summary"]
                        avg_sharpe = summary.get("sharpe")

                        logger.info(f"Avg Sharpe: {avg_sharpe} | Window 6 Sharpe: {w6_sharpe}")
                        results.append({"linkage": linkage, "avg_sharpe": avg_sharpe, "w6_sharpe": w6_sharpe})
                    except KeyError:
                        logger.warning("Could not find HRP summary in tournament results")

        except subprocess.CalledProcessError as e:
            logger.error(f"Backtest failed for {linkage}: {e.stderr.decode()}")

    print("\n--- Linkage Tournament Summary ---")
    print(pd.DataFrame(results).to_markdown())


if __name__ == "__main__":
    run_experiment()
