#!/usr/bin/env python3
"""
Check which portfolio symbols are missing historical backfill data.
"""

import logging
import os

from scripts.verify_portfolio_symbols import load_json_symbols

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("check_backfill")


def check_backfill():
    base_path = "data/lakehouse"
    files = ["portfolio_barbell.json", "portfolio_optimized.json"]

    symbols = set()
    for filename in files:
        filepath = os.path.join(base_path, filename)
        if os.path.exists(filepath):
            symbols.update(load_json_symbols(filepath))

    logger.info(f"Checking backfill status for {len(symbols)} symbols...")

    missing_backfill = []
    found_backfill = []

    for symbol in symbols:
        # Construct expected filename
        # Convention: EXCHANGE:SYMBOL -> EXCHANGE_SYMBOL_1d.parquet
        filename = f"{symbol.replace(':', '_')}_1d.parquet"
        filepath = os.path.join(base_path, filename)

        if os.path.exists(filepath):
            found_backfill.append(symbol)
        else:
            missing_backfill.append(symbol)

    logger.info(f"Found backfill for {len(found_backfill)} symbols")
    logger.warning(f"Missing backfill for {len(missing_backfill)} symbols")

    if missing_backfill:
        with open("missing_backfill.txt", "w") as f:
            for sym in sorted(missing_backfill):
                f.write(f"{sym}\n")
        logger.info("Missing symbols saved to missing_backfill.txt")


if __name__ == "__main__":
    check_backfill()
