#!/usr/bin/env python3
"""Script invoked by quant-optimize skill."""

import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from tradingview_scraper.settings import get_settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--profile", default="hrp")
    args = parser.parse_args()

    print(f"Starting optimization for run: {args.run_id} (Profile: {args.profile})")

    os.environ["TV_RUN_ID"] = args.run_id
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # We use QuantSDK to run optimization
    # Note: allocation.optimize stage must be registered
    # (Actually optimization is often profile-driven)

    from scripts.optimize_clustered_v2 import optimize_clustered_portfolio

    optimize_clustered_portfolio(run_id=args.run_id, risk_profiles=[args.profile])

    print(f"Optimization complete. Results saved to {run_dir}/data/portfolio_optimized_v2.json")


if __name__ == "__main__":
    main()
