"""
Unified Live Execution Runner.
Supports both Nautilus (Crypto/Futures) and MT5 (Forex/CFD) via the Unified OMS Interface.
"""

import argparse
import logging
import sys
import time
from typing import Optional

from tradingview_scraper.execution.adapters.mt5_adapter import Mt5OmsAdapter
from tradingview_scraper.execution.oms import ExecutionEngine

# Nautilus imports done lazily/conditionally

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("unified_runner")


def run_oms_loop(oms: ExecutionEngine):
    """
    Common execution loop using the Unified Interface.
    In a real app, this would be the Strategy Engine or Signal Handler.
    """
    logger.info("Connecting to Execution Engine...")
    oms.connect()

    try:
        # 1. Get Account State
        acct = oms.get_account_state()
        logger.info(f"Account State: Balance={acct.balance} {acct.currency}, Equity={acct.equity}")

        # 2. Get Positions
        positions = oms.get_positions()
        logger.info(f"Open Positions: {len(positions)}")
        for p in positions:
            logger.info(f"  - {p.symbol}: {p.side} {p.quantity} @ {p.avg_price} (Unrealized: {p.unrealized_pnl})")

        # 3. (Optional) Signal Logic here
        # ...

        # Keep alive
        while True:
            time.sleep(10)
            # Heartbeat or refresh
            # acct = oms.get_account_state()
            # logger.info(f"Heartbeat: Equity={acct.equity}")

    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        oms.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Unified OMS Runner")
    parser.add_argument("--engine", choices=["NAUTILUS", "MT5"], required=True, help="Execution Engine")
    parser.add_argument("--venue", type=str, default="BINANCE", help="Venue (for Nautilus)")
    parser.add_argument("--mt5-host", type=str, default="127.0.0.1", help="MT5 ZMQ Host")
    args = parser.parse_args()

    oms: Optional[ExecutionEngine] = None

    if args.engine == "MT5":
        logger.info(f"Initializing MT5 Adapter ({args.mt5_host})...")
        oms = Mt5OmsAdapter(host=args.mt5_host)
        run_oms_loop(oms)

    elif args.engine == "NAUTILUS":
        logger.info(f"Initializing Nautilus Engine ({args.venue})...")
        # Nautilus initialization is complex; it requires building the Node + Strategy first.
        # The OMS adapter wraps the Strategy instance.

        from tradingview_scraper.execution.adapters.nautilus_adapter import NautilusOmsAdapter
        from tradingview_scraper.execution.metadata import ExecutionMetadataCatalog
        from tradingview_scraper.portfolio_engines.nautilus_live import NautilusLiveEngine
        from tradingview_scraper.portfolio_engines.nautilus_live_strategy import LiveRebalanceStrategy

        # 1. Build Node
        # Force SHADOW mode for safety/testing in this runner
        engine_factory = NautilusLiveEngine(venue=args.venue, mode="SHADOW", log_level="INFO")
        node = engine_factory.build()

        if not node:
            logger.error("Failed to build Nautilus Node")
            sys.exit(1)

        # 2. Build Strategy
        catalog = ExecutionMetadataCatalog()
        # We need a dummy weights file or real one
        strategy = LiveRebalanceStrategy(weights_file="artifacts/orders/target_weights.json", venue_str=args.venue, catalog=catalog)

        # 3. Add to Node
        node.trader.add_strategy(strategy)

        # 4. Wrap with OMS Adapter
        oms = NautilusOmsAdapter(strategy)

        # 5. Run Logic
        # Problem: Nautilus Node.run() is blocking.
        # So we can't run our custom 'run_oms_loop' easily unless it runs in a separate thread
        # or we hook into Nautilus lifecycle.
        #
        # For this Unified Runner, we will start the Node in a thread (if possible) or just run the Node.
        # But 'run_oms_loop' expects to call methods on 'oms'.
        #
        # Solution: We verify the adapter *can* be instantiated, then run the Node normally.
        # The 'Unified Interface' for Nautilus is mostly for *external* control (e.g. a GUI or Flask app)
        # interacting with the running strategy.

        logger.info("Nautilus Node constructed. Wrapper ready.")
        logger.info("Starting Nautilus Node (Blocking)...")

        # We inject a small separate thread to demonstrate OMS access after startup
        import threading

        def oms_poller():
            time.sleep(5)  # Wait for node start
            logger.info("--- OMS Poller Started ---")
            logger.info("Connecting via Adapter...")
            oms.connect()
            acct = oms.get_account_state()
            logger.info(f"[OMS] Account: {acct.balance} {acct.currency}")
            pos = oms.get_positions()
            logger.info(f"[OMS] Positions: {len(pos)}")

        t = threading.Thread(target=oms_poller, daemon=True)
        t.start()

        node.run()


if __name__ == "__main__":
    main()
