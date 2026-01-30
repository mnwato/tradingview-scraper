import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


def audit_ledger_anomalies(run_id: str):
    run_dir = Path(f"artifacts/summaries/runs/{run_id}")
    audit_path = run_dir / "audit.jsonl"

    if not audit_path.exists():
        print(f"Audit ledger missing for {run_id}")
        return

    windows = defaultdict(lambda: {"select": None, "optimize": {}})

    with open(audit_path, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("type") != "action":
                    continue

                ctx = entry.get("context", {})
                w_idx = ctx.get("window_index")
                if w_idx is None:
                    continue

                step = entry.get("step")

                if step == "backtest_select":
                    windows[w_idx]["select"] = entry.get("outcome", {}).get("metrics", {})
                elif step == "backtest_optimize":
                    profile = ctx.get("profile")
                    engine = ctx.get("engine")
                    weights = entry.get("outcome", {}).get("metrics", {}).get("weights", {})
                    if profile and weights:
                        windows[w_idx]["optimize"][(engine, profile)] = weights
            except Exception:
                continue

    print(f"\n# Ledger Anomaly Audit: {run_id}")

    anomalies = []

    for w_idx, data in sorted(windows.items()):
        sel = data["select"]
        opt = data["optimize"]

        # 1. Sparse Pool Detection
        if sel:
            n_winners = sel.get("n_winners", 0)
            if n_winners < 5:
                anomalies.append({"window": w_idx, "type": "SPARSE_POOL", "severity": "HIGH" if n_winners < 3 else "MEDIUM", "details": f"Only {n_winners} winners recruited."})

        # 2. Convergence Detection
        # Compare weights across profiles for the same engine
        engines = set(e for e, p in opt.keys())
        for eng in engines:
            profiles = [p for e, p in opt.keys() if e == eng]
            if len(profiles) < 2:
                continue

            for i in range(len(profiles)):
                for j in range(i + 1, len(profiles)):
                    p1 = profiles[i]
                    p2 = profiles[j]
                    w1 = opt[(eng, p1)]
                    w2 = opt[(eng, p2)]

                    # Convert to Series for easy comparison
                    all_syms = sorted(list(set(w1.keys()) | set(w2.keys())))
                    v1 = np.array([w1.get(s, 0.0) for s in all_syms])
                    v2 = np.array([w2.get(s, 0.0) for s in all_syms])

                    # Check if identical
                    if np.allclose(v1, v2, atol=1e-8):
                        # Equal weight is naturally different if N > 1 and weights are non-uniform
                        if "equal_weight" in [p1, p2]:
                            # If EW is identical to HRP, it means HRP produced uniform weights
                            pass

                        anomalies.append({"window": w_idx, "type": "PROFILE_CONVERGENCE", "severity": "MEDIUM", "details": f"Engine {eng}: {p1} and {p2} produced identical weights."})

    if not anomalies:
        print("✅ No significant anomalies detected in rebalance ledger.")
    else:
        df_anom = pd.DataFrame(anomalies)
        print(f"❌ Found {len(anomalies)} anomalies:")
        print(df_anom.to_markdown(index=False))

        print("\n### Summary by Type:")
        print(df_anom["type"].value_counts().to_markdown())


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/audit_ledger_anomalies.py <run_id>")
    else:
        audit_ledger_anomalies(sys.argv[1])
