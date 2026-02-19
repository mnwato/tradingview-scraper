"""CLI for screening top-100 US market-cap stocks with oversold RSI and rising volume."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_screen_fn():
    from tradingview_scraper.screeners.top100_rsi_volume import (
        screen_top100_oversold_with_rising_volume,
    )

    return screen_top100_oversold_with_rising_volume


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Screen top market-cap symbols where RSI <= threshold "
            "and volume is above average volume."
        )
    )
    parser.add_argument("--market", default="america", help="TradingView market id")
    parser.add_argument("--limit", type=int, default=100, help="Universe size")
    parser.add_argument(
        "--rsi-threshold", type=float, default=30.0, help="Maximum RSI threshold"
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print output JSON"
    )
    parser.add_argument(
        "--include-universe",
        action="store_true",
        help="Include top-100 NASDAQ/NYSE universe used before RSI/volume filtering",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    screen_top100_oversold_with_rising_volume = _load_screen_fn()
    result = screen_top100_oversold_with_rising_volume(
        market=args.market,
        limit=args.limit,
        rsi_threshold=args.rsi_threshold,
        include_universe=args.include_universe,
    )
    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
