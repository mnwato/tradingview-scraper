import argparse
import json
import logging
from typing import Any, Dict

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("window_matrix_audit")


def analyze_run(run_id: str):
    log_path = f"artifacts/summaries/runs/{run_id}/audit.jsonl"
    logger.info(f"Auditing Run: {run_id}")

    entries = []
    try:
        with open(log_path, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    except FileNotFoundError:
        logger.error(f"Audit log not found: {log_path}")
        return

    # Extract Optimization Outcomes (Weights construction)
    # Step: backtest_optimize
    optimizations = [e for e in entries if e.get("step") == "backtest_optimize" and e.get("status") == "success"]

    # Extract Simulation Outcomes (Performance)
    # Step: backtest_simulate
    simulations = [e for e in entries if e.get("step") == "backtest_simulate" and e.get("status") == "success"]

    # Organize by Window
    # Structure: Window -> Engine -> Profile -> Metrics

    matrix: Dict[int, Dict[str, Dict[str, Dict[str, Any]]]] = {}

    # Process Optimizations (Construction stats)
    for opt in optimizations:
        ctx = opt.get("context", {})
        window = ctx.get("window_index")
        eng = ctx.get("engine")
        prof = ctx.get("profile")
        metrics = opt.get("outcome", {}).get("metrics", {})

        if window is None or not eng or not prof:
            continue

        if window not in matrix:
            matrix[window] = {}
        if eng not in matrix[window]:
            matrix[window][eng] = {}
        if prof not in matrix[window][eng]:
            matrix[window][eng][prof] = {}

        matrix[window][eng][prof].update(
            {
                "n_assets": metrics.get("n_assets"),
                "entropy": metrics.get("concentration_entropy", 0.0),  # If available
            }
        )

    # Process Simulations (Performance stats)
    for sim in simulations:
        ctx = sim.get("context", {})
        # Simulation context might be slightly different?
        # Checked code: it has window_index from window_context_base
        window = ctx.get("window_index")
        eng = ctx.get("engine")
        prof = ctx.get("profile")
        simulator = ctx.get("simulator")  # e.g. cvxportfolio
        metrics = sim.get("outcome", {}).get("metrics", {})

        if window is None or not eng or not prof:
            continue

        if window not in matrix:
            matrix[window] = {}  # Should have been created by optimize, but possible to have sim without opt if cached?
        if eng not in matrix[window]:
            matrix[window][eng] = {}
        if prof not in matrix[window][eng]:
            matrix[window][eng][prof] = {}

        # We might have multiple simulators. We'll prefix metrics with sim name.
        # But user asked for "simulators engines matrix".
        # Let's just grab Sharpe for now.
        matrix[window][eng][prof].update({f"{simulator}_sharpe": metrics.get("sharpe")})

    # Generate Report
    print(f"# Window-by-Window Audit Matrix ({run_id})")

    sorted_windows = sorted(matrix.keys())
    for w in sorted_windows:
        print(f"\n## Window {w}")

        # Flatten for table
        rows = []
        for eng in sorted(matrix[w].keys()):
            for prof in sorted(matrix[w][eng].keys()):
                data = matrix[w][eng][prof]
                row = {
                    "Engine": eng,
                    "Profile": prof,
                    "Assets": data.get("n_assets", "-"),
                    # "Entropy": f"{data.get('entropy', 0):.2f}",
                }
                # Add simulator sharpes
                for k, v in data.items():
                    if k.endswith("_sharpe"):
                        sim_name = k.replace("_sharpe", "")
                        row[f"Sharpe ({sim_name})"] = f"{v:.4f}" if isinstance(v, (int, float)) else str(v)

                rows.append(row)

        if rows:
            df = pd.DataFrame(rows)
            # Reorder columns nicely
            cols = ["Engine", "Profile", "Assets"] + [c for c in df.columns if "Sharpe" in c]
            # Ensure cols exist
            cols = [c for c in cols if c in df.columns]
            print(df[cols].to_markdown(index=False))
        else:
            print("No data for this window.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="20260109-193211", help="Run ID to audit")
    args = parser.parse_args()
    analyze_run(args.run_id)
