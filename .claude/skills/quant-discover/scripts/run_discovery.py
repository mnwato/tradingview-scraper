#!/usr/bin/env python3
"""Script invoked by quant-discover skill."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from tradingview_scraper.orchestration.sdk import QuantSDK
from tradingview_scraper.settings import get_settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    print(f"Starting discovery for profile: {args.profile}")

    # We use QuantSDK to run discovery
    # Note: discovery.full stage must be registered
    QuantSDK.run_stage("discovery.full", profile_name=args.profile, run_id=args.run_id)

    settings = get_settings()
    run_id = args.run_id or settings.run_id
    export_dir = settings.export_dir / run_id

    print(f"Discovery complete. Candidates exported to {export_dir}")


if __name__ == "__main__":
    main()
