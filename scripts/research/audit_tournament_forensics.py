import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from tradingview_scraper.utils.metrics import (
    calculate_friction_alignment,
    calculate_selection_jaccard,
    calculate_temporal_fragility,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("tournament_forensics")


def load_audit_data(run_id: str) -> pd.DataFrame:
    path = Path(f"artifacts/summaries/runs/{run_id}/audit.jsonl")
    if not path.exists():
        logger.error(f"Audit ledger not found at {path}")
        return pd.DataFrame()

    rows = []
    with open(path, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                # 1. Backtest Simulation Metrics
                if data.get("step") == "backtest_simulate" and data.get("status") == "success":
                    ctx = data.get("context", {})
                    outcome = data.get("outcome", {})
                    metrics = outcome.get("metrics", {})

                    rows.append(
                        {
                            "type": "simulate",
                            "selection": ctx.get("selection_mode"),
                            "rebalance": ctx.get("rebalance_mode"),
                            "simulator": ctx.get("simulator"),
                            "engine": ctx.get("engine"),
                            "profile": ctx.get("profile"),
                            "window": ctx.get("window_index"),
                            "sharpe": metrics.get("sharpe"),
                            "return": metrics.get("return"),
                            "vol": metrics.get("vol"),
                            "kappa": ctx.get("kappa", 1.0),
                        }
                    )

                # 2. Optimization Outcomes (to get winners/weights)
                if data.get("step") == "backtest_optimize" and data.get("status") == "success":
                    ctx = data.get("context", {})
                    payload = data.get("data", {})
                    weights = payload.get("weights", {})

                    rows.append(
                        {
                            "type": "optimize",
                            "selection": ctx.get("selection_mode"),
                            "rebalance": ctx.get("rebalance_mode"),
                            "engine": ctx.get("engine"),
                            "profile": ctx.get("profile"),
                            "window": ctx.get("window_index"),
                            "winners": list(weights.keys()),
                        }
                    )

                # 3. Aggregated Summary Metrics (per config)
                if data.get("step") == "backtest_summary" and data.get("status") == "success":
                    ctx = data.get("context", {})
                    outcome = data.get("outcome", {})
                    metrics = outcome.get("metrics", {})

                    rows.append(
                        {
                            "type": "summary",
                            "selection": ctx.get("selection_mode"),
                            "rebalance": ctx.get("rebalance_mode"),
                            "simulator": ctx.get("simulator"),
                            "engine": ctx.get("engine"),
                            "profile": ctx.get("profile"),
                            "af_dist": metrics.get("af_dist"),
                            "stress_alpha": metrics.get("stress_alpha"),
                            "stress_delta": metrics.get("stress_delta"),
                            "stress_ref": metrics.get("stress_ref"),
                        }
                    )
            except Exception:
                continue

    return pd.DataFrame(rows)


def audit_outliers(df: pd.DataFrame):
    if df.empty:
        return

    sim_df = df[df["type"] == "simulate"]

    logger.info("\n--- 1. Simulator Friction Audit ---")
    # Group by config and calculate mean Sharpe per simulator
    summary = sim_df.groupby(["selection", "rebalance", "engine", "profile", "simulator"])["sharpe"].mean().unstack("simulator")

    if "custom" in summary.columns and "cvxportfolio" in summary.columns:
        summary["friction_decay"] = summary.apply(lambda x: calculate_friction_alignment(x["cvxportfolio"], x["custom"]), axis=1)
        outliers = summary[summary["friction_decay"] > 0.3].sort_values("friction_decay", ascending=False)
        if not outliers.empty:
            logger.warning(f"Found {len(outliers)} configurations with >30% Sharpe decay in High-Fidelity:")
            print(outliers[["custom", "cvxportfolio", "friction_decay"]].head(10))
        else:
            logger.info("No extreme friction outliers found (<30% decay).")

    logger.info("\n--- 2. Temporal Consistency Audit ---")
    # Calculate CV of Sharpe across windows
    win_stats = sim_df.groupby(["selection", "rebalance", "simulator", "engine", "profile"])["sharpe"].apply(calculate_temporal_fragility).reset_index(name="temporal_fragility")

    # Merge back with mean Sharpe
    mean_sharpe = sim_df.groupby(["selection", "rebalance", "simulator", "engine", "profile"])["sharpe"].mean().reset_index(name="mean_sharpe")
    win_stats = pd.merge(win_stats, mean_sharpe, on=["selection", "rebalance", "simulator", "engine", "profile"])

    fragile = win_stats[(win_stats["mean_sharpe"] > 2.0) & (win_stats["temporal_fragility"] > 1.5)].sort_values("temporal_fragility", ascending=False)
    if not fragile.empty:
        logger.warning("Top configurations with high window-to-window fragility (CV > 1.5):")
        print(fragile.head(10))
    else:
        logger.info("Top configurations show good temporal consistency (CV <= 1.5).")

    logger.info("\n--- 3. Selection Stability Audit ---")
    opt_df = df[df["type"] == "optimize"].sort_values(["selection", "rebalance", "engine", "profile", "window"])

    stability_results = []
    groups = opt_df.groupby(["selection", "rebalance", "engine", "profile"])
    for name, group in groups:
        if len(group) < 2:
            continue

        jaccards = []
        winners_list = group["winners"].tolist()
        for i in range(1, len(winners_list)):
            jaccards.append(calculate_selection_jaccard(winners_list[i - 1], winners_list[i]))

        stability_results.append({"selection": name[0], "rebalance": name[1], "engine": name[2], "profile": name[3], "avg_jaccard": np.mean(jaccards) if jaccards else 1.0})

    if stability_results:
        stab_df = pd.DataFrame(stability_results).sort_values("avg_jaccard")
        unstable = stab_df[stab_df["avg_jaccard"] < 0.3]
        if not unstable.empty:
            logger.warning(f"Found {len(unstable)} configurations with unstable selection (Jaccard < 0.3):")
            print(unstable.head(10))
        else:
            logger.info("Selection logic is stable across windows (Jaccard >= 0.3).")

    logger.info("\n--- 4. Quantified Antifragility Audit ---")
    summary_df = df[df["type"] == "summary"]
    if summary_df.empty:
        logger.info("No backtest_summary entries found; enable feat_audit_ledger to compute antifragility gates.")
        return

    af = pd.merge(
        summary_df,
        mean_sharpe,
        on=["selection", "rebalance", "simulator", "engine", "profile"],
        how="left",
    )

    dist_fragile = af[(af["mean_sharpe"] > 2.0) & af["af_dist"].notna() & (af["af_dist"] < 0.0)].sort_values("af_dist")
    if not dist_fragile.empty:
        logger.warning("High-Sharpe configurations failing distribution antifragility (AF_dist < 0):")
        print(dist_fragile[["selection", "rebalance", "simulator", "engine", "profile", "mean_sharpe", "af_dist"]].head(10))
    else:
        logger.info("No high-Sharpe configs flagged as distribution-fragile (AF_dist < 0).")

    stress_fragile = af[(af["mean_sharpe"] > 2.0) & af["stress_alpha"].notna() & (af["stress_alpha"] < 0.0)].sort_values("stress_alpha")
    if not stress_fragile.empty:
        logger.warning("High-Sharpe configurations failing stress antifragility (stress_alpha < 0):")
        print(stress_fragile[["selection", "rebalance", "simulator", "engine", "profile", "mean_sharpe", "stress_alpha", "stress_delta", "stress_ref"]].head(10))
    else:
        logger.info("No high-Sharpe configs flagged as crisis-fragile (stress_alpha < 0).")

    leaders = af[(af["mean_sharpe"] > 2.0) & af["af_dist"].notna() & (af["af_dist"] >= 0.25) & af["stress_alpha"].notna() & (af["stress_alpha"] >= 0.0)].sort_values("mean_sharpe", ascending=False)
    if not leaders.empty:
        logger.info("Top robust + antifragile candidates (mean_sharpe > 2.0, AF_dist >= 0.25, stress_alpha >= 0):")
        print(leaders[["selection", "rebalance", "simulator", "engine", "profile", "mean_sharpe", "af_dist", "stress_alpha", "stress_delta", "stress_ref"]].head(10))


def main():
    run_id = "20260104-005636"
    df = load_audit_data(run_id)
    if df.empty:
        return

    audit_outliers(df)


if __name__ == "__main__":
    main()
