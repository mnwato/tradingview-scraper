import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("tournament_reporter")


def _fmt_num(val: Any, fmt: str = ".2f") -> str:
    try:
        if val is None or pd.isna(val):
            return "N/A"
        return format(float(val), fmt)
    except (ValueError, TypeError):
        return str(val)


def generate_grand_table(results_path: str, output_path: str):
    path = Path(results_path)
    if not path.exists():
        logger.error(f"Results not found at {path}")
        return

    with open(path, "r") as f:
        data = json.load(f)

    results = data.get("rebalance_audit_results", {})
    rows = []

    for reb_mode, selections in results.items():
        if selections is None:
            continue
        for sel_mode, simulators in selections.items():
            if simulators is None:
                continue
            for sim, engines in simulators.items():
                if sim == "_status" or engines is None:
                    continue
                for eng, profiles in engines.items():
                    if eng == "_status" or profiles is None:
                        continue
                    for prof, details in profiles.items():
                        if prof == "_status" or details is None:
                            continue
                        summ = details.get("summary", {})
                        if not summ:
                            continue

                        rows.append(
                            {
                                "Selection": sel_mode,
                                "Rebalance": reb_mode,
                                "Simulator": sim,
                                "Engine": eng,
                                "Profile": prof,
                                "Sharpe": summ.get("avg_window_sharpe"),
                                "Return": summ.get("annualized_return"),
                                "Vol": summ.get("annualized_vol"),
                                "MDD": summ.get("max_drawdown"),
                                "Turnover": summ.get("avg_turnover"),
                            }
                        )

    if not rows:
        logger.warning("No data found in results.")
        return

    df = pd.DataFrame(rows)
    df = df.sort_values("Sharpe", ascending=False)

    # Format percentages
    for col in ["Return", "Vol", "MDD", "Turnover"]:
        df[col] = df[col].apply(lambda x: _fmt_num(x, ".2%"))
    df["Sharpe"] = df["Sharpe"].apply(lambda x: _fmt_num(x, ".2f"))

    md = ["# Grand 4D Tournament Report", f"Run ID: {data.get('meta', {}).get('run_id', 'N/A')}", f"Total Configurations: {len(df)}", "", df.to_markdown(index=False)]

    with open(output_path, "w") as f:
        f.write("\n".join(md))

    logger.info(f"✅ Grand Table generated: {output_path}")
    print(f"\n{df.head(20).to_markdown(index=False)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="artifacts/summaries/latest/grand_4d_tournament_results_partial.json")
    parser.add_argument("--output", default="artifacts/summaries/latest/reports/engine/grand_4d_table.md")
    args = parser.parse_args()

    generate_grand_table(args.input, args.output)
