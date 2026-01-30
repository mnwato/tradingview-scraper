"""
Script to run the Nautilus Live Engine in SHADOW mode (L5.5).
Executes the LiveRebalanceStrategy against real data but paper fills.
"""

import argparse
import logging

from tradingview_scraper.execution.metadata import ExecutionMetadataCatalog
from tradingview_scraper.portfolio_engines.nautilus_live import NautilusLiveEngine
from tradingview_scraper.portfolio_engines.nautilus_live_strategy import LiveRebalanceStrategy
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_live_shadow")


def main():
    settings = get_settings()
    default_weights = str(settings.artifacts_dir / "orders/target_weights.json")

    parser = argparse.ArgumentParser(description="Run Nautilus Live Shadow Loop")
    parser.add_argument("--venue", type=str, default="BINANCE", help="Venue (BINANCE, IBKR)")
    parser.add_argument("--weights-file", type=str, default=default_weights, help="Path to weights file")
    args = parser.parse_args()

    logger.info(f"Initializing Shadow Loop for {args.venue}...")

    # 1. Build Engine
    engine = NautilusLiveEngine(venue=args.venue, mode="SHADOW", log_level="INFO")
    node = engine.build()

    if not node:
        logger.error("Failed to build TradingNode. Exiting.")
        return

    # 2. Prepare Strategy
    catalog = ExecutionMetadataCatalog()
    strategy = LiveRebalanceStrategy(weights_file=args.weights_file, venue_str=args.venue, catalog=catalog)

    # 3. Register Strategy
    # Note: In a real node, we need to add the strategy to the node.
    # TradingNode.trader.add_strategy() handles this.
    try:
        node.trader.add_strategy(strategy)
        logger.info("Strategy registered.")
    except Exception as e:
        logger.error(f"Failed to add strategy: {e}")
        return

    # 4. Run
    logger.info("Starting Node (Ctrl+C to stop)...")
    try:
        node.run()
    except KeyboardInterrupt:
        logger.info("Stopping...")
        node.stop()
    except Exception as e:
        logger.error(f"Runtime error: {e}")


if __name__ == "__main__":
    main()
