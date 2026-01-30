#!/usr/bin/env python3
import logging

from scripts.build_metadata_catalog import fetch_tv_metadata
from tradingview_scraper.symbols.stream.metadata import DEFAULT_EXCHANGE_METADATA, ExchangeCatalog, MetadataCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_missing_build")


def main():
    try:
        with open("missing_portfolio_symbols.txt", "r") as f:
            symbols = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error("missing_portfolio_symbols.txt not found")
        return

    if not symbols:
        logger.info("No missing symbols to process")
        return

    logger.info(f"Fetching metadata for {len(symbols)} missing symbols...")

    # Fetch metadata
    catalog_data = fetch_tv_metadata(symbols)

    if catalog_data:
        logger.info(f"Upserting {len(catalog_data)} records to catalog")

        # Upsert symbols
        catalog = MetadataCatalog()
        catalog.upsert_symbols(catalog_data)

        # Ensure exchange metadata exists for these
        ex_catalog = ExchangeCatalog()
        exchanges = {r["exchange"] for r in catalog_data if r.get("exchange")}
        for ex in exchanges:
            defaults = DEFAULT_EXCHANGE_METADATA.get(ex)
            if defaults:
                ex_catalog.upsert_exchange(
                    {
                        "exchange": ex,
                        "timezone": defaults.get("timezone", "UTC"),
                        "is_crypto": bool(defaults.get("is_crypto", False)),
                        "country": defaults.get("country", "Global"),
                        "description": defaults.get("description", f"{ex} Exchange"),
                    }
                )

        logger.info("Build complete")
    else:
        logger.warning("No data fetched")


if __name__ == "__main__":
    main()
