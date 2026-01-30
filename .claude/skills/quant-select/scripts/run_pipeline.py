#!/usr/bin/env python3
"""Script invoked by quant-select skill."""

import argparse
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.run_production_pipeline import ProductionPipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    print(f"Running selection for profile: {args.profile}")

    pipeline = ProductionPipeline(profile=args.profile, run_id=args.run_id)
    pipeline.execute()

    print("Selection complete.")


if __name__ == "__main__":
    main()
