import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("forensic_audit")

RUNS = ["val_agg_all_209", "val_agg_ma_209"]


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        return {}


def analyze_run(run_id: str) -> Dict[str, Any]:
    base_dir = Path(f"artifacts/summaries/runs/{run_id}/data")

    # 1. Selection Stats
    candidates_path = base_dir / "portfolio_candidates.json"
    candidates_raw_path = base_dir / "portfolio_candidates_raw.json"

    sel_data = load_json(candidates_path)
    raw_data = load_json(candidates_raw_path)

    n_raw = len(raw_data) if isinstance(raw_data, list) else 0
    n_sel = len(sel_data) if isinstance(sel_data, list) else 0

    # 2. Validation Stats (Tournament)
    tourn_path = base_dir / "tournament_results.json"
    tourn_data = load_json(tourn_path)

    results = {}

    # Profile Metrics
    profile_metrics = {}
    if "results" in tourn_data:
        # Sort results to prioritize cvxportfolio/vectorbt over nautilus for the forensic summary
        # Assuming order in list is arbitrary, we create a map first
        sim_priority = {"cvxportfolio": 3, "vectorbt": 2, "nautilus": 1}

        # Group by profile+engine+simulator to aggregate across windows
        grouped = {}
        for res in tourn_data["results"]:
            p_name = res.get("profile")
            engine = res.get("engine")
            simulator = res.get("simulator")

            if engine not in ["custom", "skfolio"]:
                continue

            key = f"{p_name}_{engine}_{simulator}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(res["metrics"])

        # Select best simulator for each profile+engine (based on priority of averaged metrics? or just preference)
        # We want to show ONE row per profile/engine.
        # Priority: cvxportfolio > vectorbt > nautilus

        final_metrics = {}  # Key: profile_engine

        sim_priority = ["cvxportfolio", "vectorbt", "nautilus"]

        # organizing keys by profile_engine
        pe_map = {}
        for k in grouped.keys():
            p_e = "_".join(k.split("_")[:-1])  # remove simulator suffix
            sim = k.split("_")[-1]
            if p_e not in pe_map:
                pe_map[p_e] = []
            pe_map[p_e].append(sim)

        for p_e, sims in pe_map.items():
            # Pick best sim
            best_sim = next((s for s in sim_priority if s in sims), sims[0])
            full_key = f"{p_e}_{best_sim}"

            # Average metrics across windows
            metrics_list = grouped[full_key]
            n = len(metrics_list)
            if n == 0:
                continue

            avg_sharpe = sum(m.get("sharpe", 0.0) for m in metrics_list) / n
            avg_cagr = sum(m.get("annualized_return", 0.0) for m in metrics_list) / n
            avg_vol = sum(m.get("annualized_vol", 0.0) for m in metrics_list) / n
            avg_mdd = sum(m.get("max_drawdown", 0.0) for m in metrics_list) / n
            avg_total = sum(m.get("total_return", 0.0) for m in metrics_list) / n

            cagr_str = f"{avg_cagr:.2f}%"
            if avg_cagr >= 100.0:
                cagr_str = ">100% (Capped)"

            profile_metrics[p_e] = {"sharpe": avg_sharpe, "cagr_display": cagr_str, "vol_display": f"{avg_vol:.2f}", "mdd": avg_mdd, "total_ret": avg_total, "simulator": best_sim}

    return {"run_id": run_id, "n_raw": n_raw, "n_sel": n_sel, "profiles": profile_metrics}

    return {"run_id": run_id, "n_raw": n_raw, "n_sel": n_sel, "profiles": profile_metrics}


def generate_report():
    logger.info("Generating Forensic Audit Report...")

    aggregated = []
    for run in RUNS:
        logger.info(f"Analyzing {run}...")
        data = analyze_run(run)
        aggregated.append(data)

    # --- Generate Markdown ---
    lines = []
    lines.append("# 🔍 Stable Forensic Audit Report (Phase 176)")
    lines.append(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("\n## 1. Pipeline Funnel Summary")
    lines.append("| Run ID | Raw Pool | Selected | Selection Rate |")
    lines.append("| :--- | :---: | :---: | :---: |")

    for row in aggregated:
        rate = (row["n_sel"] / row["n_raw"]) * 100 if row["n_raw"] > 0 else 0
        lines.append(f"| `{row['run_id']}` | {row['n_raw']} | {row['n_sel']} | {rate:.1f}% |")

    lines.append("\n## 2. Performance Matrix (Custom Engine)")
    lines.append("| Run ID | Profile | Simulator | Sharpe | Total Ret | CAGR | Volatility | MaxDD |")
    lines.append("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |")

    anomalies = []

    for row in aggregated:
        sorted_keys = sorted(row["profiles"].keys())
        for p_key in sorted_keys:
            metrics = row["profiles"][p_key]
            if "custom" not in p_key:
                continue
            profile = p_key.replace("_custom", "")

            # Anomaly Detection
            if metrics["sharpe"] > 8.0:
                anomalies.append(f"⚠️ {row['run_id']} ({profile}): Extreme Sharpe {metrics['sharpe']:.2f}")
            if metrics["sharpe"] < -2.0:
                anomalies.append(f"⚠️ {row['run_id']} ({profile}): Negative Sharpe {metrics['sharpe']:.2f} (Expected for Shorts)")

            lines.append(
                f"| `{row['run_id']}` | {profile} | {metrics['simulator']} | {metrics['sharpe']:.2f} | {metrics['total_ret']:.2f}X | {metrics['cagr_display']} | {metrics['vol_display']} | {metrics['mdd']:.2%} |"
            )

    if anomalies:
        lines.append("\n## 3. Anomaly Detection (Outliers)")
        for a in anomalies:
            lines.append(f"- {a}")
    else:
        lines.append("\n## 3. Anomaly Detection")
        lines.append("✅ No statistical outliers detected.")

    report_path = "docs/reports/stable_forensic_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    logger.info(f"Report saved to {report_path}")
    print("\n".join(lines))


if __name__ == "__main__":
    generate_report()
