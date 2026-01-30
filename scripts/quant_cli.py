#!/usr/bin/env python3
import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.orchestration.sdk import QuantSDK

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("quant_cli")


def handle_stage_list(args):
    stages = StageRegistry.list_stages(tag=args.tag, category=args.category)
    if not stages:
        print("No stages found.")
        return

    print(f"{'ID':<30} {'NAME':<30} {'CATEGORY':<15}")
    print("-" * 75)
    for s in stages:
        print(f"{s.id:<30} {s.name:<30} {s.category:<15}")


def handle_stage_run(args):
    # Parse params if provided
    params = {}
    if args.param:
        for p in args.param:
            if "=" in p:
                k, v = p.split("=", 1)
                params[k] = v

    # run_id fallback to env or current date
    run_id = args.run_id or "cli_" + Path(".").resolve().name

    try:
        result = QuantSDK.run_stage(args.id, run_id=run_id, **params)
        print(f"Stage {args.id} completed successfully.")
        # If result is a context or dict, print summary?
    except Exception as e:
        logger.error(f"Failed to run stage {args.id}: {e}", exc_info=args.verbose)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Quantitative Portfolio Platform CLI")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Stage Command
    stage_parser = subparsers.add_parser("stage", help="Pipeline stage operations")
    stage_sub = stage_parser.add_subparsers(dest="subcommand")

    # Stage List
    list_parser = stage_sub.add_parser("list", help="List registered stages")
    list_parser.add_argument("--tag", help="Filter by tag")
    list_parser.add_argument("--category", help="Filter by category")

    # Stage Run
    run_parser = stage_sub.add_parser("run", help="Run a specific stage")
    run_parser.add_argument("id", help="Stage ID")
    run_parser.add_argument("--run-id", help="Explicit run ID")
    run_parser.add_argument("--param", action="append", help="Parameter in KEY=VALUE format")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.command == "stage":
        if args.subcommand == "list":
            handle_stage_list(args)
        elif args.subcommand == "run":
            handle_stage_run(args)
        else:
            stage_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
