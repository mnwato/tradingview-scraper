import json
from pathlib import Path

import pandas as pd


def generate_ledger_audit_report(run_id: str):
    run_dir = Path(f"artifacts/summaries/runs/{run_id}")
    audit_path = run_dir / "audit.jsonl"

    if not audit_path.exists():
        return

    entries = []
    with open(audit_path, "r") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    md = []
    md.append(f"# 🕵️ Detailed Ledger Audit: {run_id}")
    md.append(f"**Generated:** {pd.Timestamp.now()}")
    md.append("\n---")

    # 1. Pipeline Execution Trace
    md.append("\n## 1. Pipeline Execution Trace")
    md.append("| Step | Status | Duration | Metrics |")
    md.append("| :--- | :--- | :--- | :--- |")

    for e in entries:
        if e.get("type") == "action" and e.get("status") == "success":
            step = e.get("step", "N/A")
            # Only show high-level pipeline steps here, skip backtest windows
            if step in ["backtest_select", "backtest_optimize", "backtest_simulate"]:
                continue

            metrics = e.get("outcome", {}).get("metrics", {})
            m_str = ", ".join([f"{k}: {v}" for k, v in metrics.items() if isinstance(v, (int, float))])
            md.append(f"| {step.upper()} | ✅ | N/A | {m_str} |")

    # 2. Window-by-Window Rebalance Audit
    md.append("\n## 2. Walk-Forward Rebalance Audit (First 5 Windows)")

    windows = {}
    for e in entries:
        if e.get("type") == "action":
            w_idx = e.get("context", {}).get("window_index")
            if w_idx is not None:
                if w_idx not in windows:
                    windows[w_idx] = {"select": None, "opt": [], "sim": []}
                step = e.get("step")
                if step == "backtest_select":
                    windows[w_idx]["select"] = e
                elif step == "backtest_optimize":
                    windows[w_idx]["opt"].append(e)
                elif step == "backtest_simulate":
                    windows[w_idx]["sim"].append(e)

    for w_idx in sorted(windows.keys())[:5]:
        data = windows[w_idx]
        md.append(f"\n### 🪟 Window {w_idx}")

        # Selection
        if data["select"]:
            sel_m = data["select"].get("outcome", {}).get("metrics", {})
            md.append(f"- **Pool**: {sel_m.get('n_discovery_candidates')} discovery -> {sel_m.get('n_winners')} winners.")
            md.append(f"- **Winners**: `{', '.join(sel_m.get('winners', []))}`")

        # Optimization (Best Profile)
        if data["opt"]:
            md.append("\n| Profile | Best Asset | Max Weight |")
            md.append("| :--- | :--- | :--- |")
            for opt in data["opt"]:
                p = opt.get("context", {}).get("profile")
                weights = opt.get("outcome", {}).get("metrics", {}).get("weights", {})
                if weights:
                    best = max(weights, key=weights.get)
                    md.append(f"| {p} | `{best}` | {weights[best]:.2%} |")

    output_path = run_dir / "ledger_audit_report.md"
    with open(output_path, "w") as f:
        f.write("\n".join(md))
    print(f"✅ Ledger audit report generated at: {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_ledger_report.py <run_id>")
    else:
        generate_ledger_audit_report(sys.argv[1])
