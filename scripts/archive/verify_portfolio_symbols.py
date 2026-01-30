#!/usr/bin/env python3
"""
Verify that all symbols in the portfolio files exist in the metadata catalog.
"""

import json
import logging
import os
from typing import Set

from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_portfolio")


def load_json_symbols(filepath: str) -> Set[str]:
    """Extract symbols from portfolio JSON files."""
    symbols = set()
    try:
        with open(filepath, "r") as f:
            data = json.load(f)

        # Handle portfolio_barbell.json format: {"Symbol": {"id": "EX:SYM", ...}}
        if "Symbol" in data:
            symbols.update(data["Symbol"].values())

        # Handle portfolio_optimized.json format: {"Min_Var_Weight": {"EX:SYM": weight, ...}}
        if "Min_Var_Weight" in data:
            symbols.update(data["Min_Var_Weight"].keys())

        logger.info(f"Loaded {len(symbols)} unique symbols from {os.path.basename(filepath)}")
        return symbols
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return set()


def verify_symbols():
    """Check portfolio symbols against catalog."""
    base_path = "data/lakehouse"
    files = ["portfolio_barbell.json", "portfolio_optimized.json"]

    all_portfolio_symbols = set()
    for filename in files:
        filepath = os.path.join(base_path, filename)
        if os.path.exists(filepath):
            all_portfolio_symbols.update(load_json_symbols(filepath))
        else:
            logger.warning(f"Portfolio file not found: {filepath}")

    logger.info(f"Total unique portfolio symbols to verify: {len(all_portfolio_symbols)}")

    # Load catalog
    catalog = MetadataCatalog()
    catalog_symbols = set(catalog._df["symbol"].unique())

    missing_symbols = all_portfolio_symbols - catalog_symbols

    if missing_symbols:
        logger.warning(f"Found {len(missing_symbols)} missing symbols in catalog!")
        for sym in sorted(missing_symbols):
            print(f"MISSING: {sym}")

        # Save missing symbols to a file for easy input to build script
        with open("missing_portfolio_symbols.txt", "w") as f:
            for sym in sorted(missing_symbols):
                f.write(f"{sym}\n")
        logger.info("Missing symbols saved to missing_portfolio_symbols.txt")
    else:
        logger.info("✅ All portfolio symbols are present in the catalog.")


if __name__ == "__main__":
    verify_symbols()
