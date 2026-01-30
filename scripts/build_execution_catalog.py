import argparse
import logging
from typing import Dict, List

import ccxt

from tradingview_scraper.execution.metadata import ExecutionMetadataCatalog

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("build_execution_catalog")


def fetch_binance_limits() -> List[Dict]:
    """Fetches execution limits from Binance using CCXT."""
    logger.info("Connecting to Binance...")
    exchange = ccxt.binance(
        {
            "enableRateLimit": True,
        }
    )

    markets = exchange.load_markets()
    logger.info(f"Fetched {len(markets)} markets from Binance.")

    limits_data = []
    for symbol, market in markets.items():
        # Map CCXT symbol to our unified BINANCE:SYMBOL format
        unified_symbol = f"BINANCE:{market['id']}"

        # CCXT precision and limits
        precision = market.get("precision", {})
        limits = market.get("limits", {})

        limits_data.append(
            {
                "symbol": unified_symbol,
                "venue": "BINANCE",
                "lot_size": float(limits.get("amount", {}).get("min", 0.0)) if limits.get("amount", {}).get("min") is not None else 0.0,
                "min_notional": float(limits.get("cost", {}).get("min", 0.0)) if limits.get("cost", {}).get("min") is not None else 0.0,
                "step_size": float(precision.get("amount", 0.0)) if precision.get("amount") is not None else 0.0,
                "tick_size": float(precision.get("price", 0.0)) if precision.get("price") is not None else 0.0,
                "maker_fee": float(market.get("maker", 0.001)),
                "taker_fee": float(market.get("taker", 0.001)),
                "contract_size": float(market.get("contractSize", 1.0)) if market.get("contractSize") is not None else 1.0,
            }
        )

    return limits_data


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Execution Metadata Catalog")
    parser.add_argument("--venue", type=str, default="BINANCE", help="Venue to fetch (default: BINANCE)")
    args = parser.parse_args()

    catalog = ExecutionMetadataCatalog()

    if args.venue.upper() == "BINANCE":
        limits = fetch_binance_limits()
        catalog.upsert_limits(limits)
        logger.info(f"Successfully updated {len(limits)} symbols for BINANCE.")
    else:
        logger.error(f"Venue {args.venue} not yet supported.")


if __name__ == "__main__":
    main()
