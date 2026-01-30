import pandas as pd
import numpy as np
from pathlib import Path


def inspect_cvx_internals(run_id, profile="barbell"):
    # Load the audit ledger
    path = Path(f"artifacts/summaries/runs/{run_id}/audit.jsonl")
    if not path.exists():
        print("Audit not found.")
        return

    with open(path, "r") as f:
        for line in f:
            import json

            data = json.loads(line)
            if data.get("step") == "backtest_simulate" and data.get("status") == "success":
                ctx = data.get("context", {})
                if ctx.get("profile") == profile and ctx.get("simulator") == "cvxportfolio":
                    metrics = data.get("outcome", {}).get("metrics", {})
                    wealth = data.get("outcome", {}).get("data", {}).get("final_holdings", {}).get("sum")  # Wait, I didn't save sum
                    holdings = data.get("outcome", {}).get("data", {}).get("final_holdings")
                    if holdings:
                        v = sum(holdings.values())
                        v_abs = sum(abs(x) for x in holdings.values())
                        print(f"Window {ctx['window_index']}: Wealth={v:.6f}, Gross={v_abs:.6f}, Ret={metrics['total_return']:.4f}")


if __name__ == "__main__":
    inspect_cvx_internals("final_v8_long_all", "barbell")
