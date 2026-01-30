import argparse
import os
from pathlib import Path

import pandas as pd


def audit_lakehouse_spikes(delete=False):
    lake_dir = Path("data/lakehouse")
    corrupted_files = []

    print("Scanning Lakehouse for Data Corruption (Spikes > 500%)...")

    for p_file in lake_dir.glob("*_1d.parquet"):
        try:
            df = pd.read_parquet(p_file)
            if "close" not in df.columns:
                continue

            # Check for extreme returns
            pct = df["close"].pct_change().dropna()
            if pct.empty:
                continue

            max_spike = pct.max()
            min_spike = pct.min()

            # Threshold: +500% (5.0) or -99% (-0.99)
            if max_spike > 5.0 or min_spike < -0.99:
                print(f"❌ CORRUPTED: {p_file.name}")
                print(f"   Max Spike: {max_spike:.2%} | Min Spike: {min_spike:.2%}")

                # Check price range
                min_price = df["close"].min()
                max_price = df["close"].max()
                print(f"   Price Range: {min_price} - {max_price}")

                corrupted_files.append(p_file)

        except Exception as e:
            print(f"Error reading {p_file}: {e}")

    if delete and corrupted_files:
        print(f"\nDeleting {len(corrupted_files)} corrupted files...")
        for f in corrupted_files:
            try:
                os.remove(f)
                print(f"Deleted: {f}")
            except Exception as e:
                print(f"Failed to delete {f}: {e}")
    elif corrupted_files:
        print(f"\nFound {len(corrupted_files)} corrupted files. Run with --delete to remove them.")
    else:
        print("\nNo data spikes detected.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true", help="Delete corrupted files")
    args = parser.parse_args()

    audit_lakehouse_spikes(delete=args.delete)
