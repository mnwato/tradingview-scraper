import json
from pathlib import Path

import pandas as pd


def analyze_run(run_id: str):
    run_dir = Path(f"artifacts/summaries/runs/{run_id}")
    results_path = run_dir / "data" / "tournament_results.json"

    if not results_path.exists():
        print(f"Results missing for {run_id}")
        return

    with open(results_path, "r") as f:
        data = json.load(f)

    flat_results = []
    # results format is a list of window dicts: [{"window": i, "engine": e, "profile": p, "simulator": s, "metrics": {...}}, ...]
    results = data.get("results", [])
    for res in results:
        window = res["window"]
        engine = res["engine"]
        profile = res["profile"]
        simulator = res["simulator"]
        metrics = res["metrics"]

        row = {
            "window": window,
            "engine": engine,
            "profile": profile,
            "simulator": simulator,
            "sharpe": metrics.get("sharpe"),
            "ann_return": metrics.get("annualized_return"),
            "vol": metrics.get("annualized_vol"),
            "max_dd": metrics.get("max_drawdown"),
        }
        flat_results.append(row)

    df = pd.DataFrame(flat_results)
    if df.empty:
        print(f"No valid results in {run_id}")
        return

    print(f"\n# Tournament Audit: {run_id}")

    # 1. Engine Performance (Mean Sharpe)
    print("\n## 1. Portfolio Engine Matrix (Mean Sharpe)")
    matrix = df.pivot_table(index="profile", columns="engine", values="sharpe", aggfunc="mean").round(4)
    print(matrix.to_markdown())

    # 2. Simulator Stability (Mean Sharpe)
    print("\n## 2. Simulator Performance Matrix (Mean Sharpe)")
    sim_matrix = df.pivot_table(index="profile", columns="simulator", values="sharpe", aggfunc="mean").round(4)
    print(sim_matrix.to_markdown())

    # 3. Risk Profile Summary
    print("\n## 3. Risk Profile Comparison (Averaged across Engines/Simulators)")
    risk_summary = df.groupby("profile").agg({"sharpe": "mean", "ann_return": "mean", "vol": "mean", "max_dd": "mean"}).round(4)
    print(risk_summary.to_markdown())

    # 4. Success Rates (Positive Sharpe Windows)
    print("\n## 4. Window Success Rates (% Positive Sharpe)")
    df["win"] = df["sharpe"] > 0
    success = (df.groupby(["profile", "engine"])["win"].mean() * 100).round(2).unstack()
    print(success.to_markdown())


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/audit_tournament_matrix.py <run_id>")
    else:
        analyze_run(sys.argv[1])
