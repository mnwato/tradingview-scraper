import json
import logging

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("audit_replay")


def replay_audit(run_id: str):
    log_path = f"artifacts/summaries/runs/{run_id}/audit.jsonl"
    logger.info(f"Replaying Audit Log: {log_path}")

    entries = []
    with open(log_path, "r") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    # Filter for Optimization Steps
    optimizations = [e for e in entries if e.get("step") == "backtest_optimize" and e.get("status") == "success"]

    logger.info(f"Found {len(optimizations)} optimization steps.")

    metrics_list = []
    for e in optimizations:
        m = e.get("outcome", {}).get("metrics", {})
        # Add context for grouping
        m["window_index"] = e.get("context", {}).get("window_index")
        m["engine"] = e.get("context", {}).get("engine")
        m["profile"] = e.get("context", {}).get("profile")
        metrics_list.append(m)

    df = pd.DataFrame(metrics_list)
    if not df.empty:
        print("\n--- Optimization Metrics Summary ---")
        print(df.describe().to_markdown())

    # Check Regime Consistency
    regimes = [e.get("context", {}).get("regime") for e in optimizations]
    print(f"\nRegimes encountered: {set(regimes)}")

    # Check for anomalies
    for m in metrics_list:
        n_assets = m.get("n_assets", 0)
        if n_assets < 2 and not m.get("baseline"):
            logger.warning(f"Low asset count ({n_assets}) in window {m.get('window_index')}")


if __name__ == "__main__":
    replay_audit("20260109-193211")
