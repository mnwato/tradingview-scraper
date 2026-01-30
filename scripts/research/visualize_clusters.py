import argparse
import json
import os

import pandas as pd


def visualize_clusters(run_id: str):
    path = f"artifacts/summaries/runs/{run_id}/data/metadata/portfolio_optimized_v2.json"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, "r") as f:
        data = json.load(f)

    registry = data.get("cluster_registry", {})

    rows = []
    for c_id, details in registry.items():
        symbols = details.get("symbols", [])
        primary_sector = details.get("primary_sector", "N/A")

        # Format symbol list nicely
        # Split into short names if possible (e.g. remove BINANCE: and USDT.P)
        short_symbols = [s.split(":")[1].replace("USDT.P", "").replace("USDT", "") for s in symbols]
        symbols_str = ", ".join(short_symbols)

        rows.append({"Cluster": c_id, "Size": len(symbols), "Sector": primary_sector, "Assets": symbols_str})

    df = pd.DataFrame(rows)

    # Sort by Size descending
    df = df.sort_values("Size", ascending=False)

    print(f"# Cluster Composition Table ({run_id})\n")
    print(df.to_markdown(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="20260109-175648")
    args = parser.parse_args()
    visualize_clusters(args.run_id)
