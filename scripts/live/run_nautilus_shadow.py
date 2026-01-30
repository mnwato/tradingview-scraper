import argparse
import logging
import os
import signal
import sys
from typing import Literal, cast

from tradingview_scraper.portfolio_engines.nautilus_live import NautilusLiveEngine
from tradingview_scraper.portfolio_engines.nautilus_live_strategy import LiveRebalanceStrategy, HAS_NAUTILUS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("nautilus_shadow_runner")


def run_node(profile: str, weights_file: str, mode: str = "SHADOW", venue: str = "BINANCE"):
    if not HAS_NAUTILUS:
        logger.error("NautilusTrader not installed. Aborting.")
        sys.exit(1)

    mode_lit = cast(Literal["LIVE", "SHADOW"], mode.upper())
    logger.info(f"🚀 Starting Nautilus {mode_lit} for profile: {profile}")
    logger.info(f"Watching weights file: {weights_file}")

    # 1. Initialize Engine
    live_engine = NautilusLiveEngine(venue=venue, mode=mode_lit)
    node = live_engine.build()

    if not node:
        logger.error("Failed to build Nautilus node.")
        sys.exit(1)

    # 2. Add Strategy
    # Using instance addition as seen in scripts/run_live_shadow.py
    strategy = LiveRebalanceStrategy(weights_file=weights_file, venue_str=venue, mode=mode_lit)

    try:
        # In this version of Nautilus, node.trader.add_strategy(strategy) is the way
        node.trader.add_strategy(strategy)
        logger.info("Strategy registered successfully.")
    except Exception as e:
        logger.error(f"Failed to add strategy: {e}")
        sys.exit(1)

    # 3. Handle Signals
    def signal_handler(sig, frame):
        logger.info("Stopping Nautilus node...")
        node.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 4. Run
    logger.info("Running Nautilus node (Press Ctrl+C to stop)")
    try:
        node.run()
    except Exception as e:
        logger.error(f"Node execution failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nautilus Live/Shadow Runner")
    parser.add_argument("--profile", default="institutional_etf", help="Optimization profile")
    parser.add_argument("--weights", default="data/lakehouse/portfolio_optimized_v3.json", help="Path to weights file")
    parser.add_argument("--mode", default="SHADOW", choices=["LIVE", "SHADOW"], help="Execution mode")
    parser.add_argument("--venue", default="BINANCE", help="Venue (BINANCE, IBKR)")
    args = parser.parse_args()

    if not os.path.exists(args.weights):
        logger.error(f"Weights file not found: {args.weights}")
        sys.exit(1)

    run_node(args.profile, args.weights, mode=args.mode, venue=args.venue)
