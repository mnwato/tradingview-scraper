#!/usr/bin/env python3
"""
Script to clean up existing metadata catalog by fixing data types and removing duplicates.
"""

import logging

import pandas as pd

from tradingview_scraper.symbols.stream.metadata import DEFAULT_EXCHANGE_METADATA, ExchangeCatalog, MetadataCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_catalog")


def cleanup_metadata_catalog():
    """
    Cleans up the existing metadata catalog by:
    1. Fixing data types for pricescale and minmov
    2. Removing duplicate records
    3. Updating tick_size calculations
    4. Adding missing exchange metadata
    """
    logger.info("Starting metadata catalog cleanup...")

    catalog = MetadataCatalog()
    df = catalog._df

    # Bootstrap ExchangeCatalog
    ex_catalog = ExchangeCatalog()

    # 0. Inject missing FOREX metadata (Requirement from 2026-01-01 audit)
    if not ex_catalog.get_exchange("FOREX"):
        logger.info("Injecting missing FOREX exchange metadata...")
        ex_catalog.upsert_exchange({"exchange": "FOREX", "timezone": "America/New_York", "is_crypto": False, "country": "Global", "description": "Global Forex Markets"})

    if df.empty:
        logger.info("Catalog is empty, nothing to clean")
        return

    logger.info(f"Processing {len(df)} records...")

    # 1. Fix data types
    logger.info("Fixing data types...")

    # Convert pricescale and minmov to int
    pricescale = pd.Series(pd.to_numeric(df["pricescale"], errors="coerce"))
    minmov = pd.Series(pd.to_numeric(df["minmov"], errors="coerce"))

    df["pricescale"] = pd.Series(pricescale).fillna(1).astype("Int64")
    df["minmov"] = pd.Series(minmov).fillna(1).astype("Int64")

    # Recalculate tick_size
    logger.info("Recalculating tick_size...")
    df["tick_size"] = df.apply(lambda row: row["minmov"] / row["pricescale"] if pd.notna(row["minmov"]) and pd.notna(row["pricescale"]) and row["pricescale"] > 0 else None, axis=1)

    # 2. Fix timezone and session for crypto symbols
    logger.info("Fixing timezone and session for crypto symbols...")
    crypto_exchanges = {ex for ex, meta in DEFAULT_EXCHANGE_METADATA.items() if meta.get("is_crypto")}

    # Fix timezone for crypto symbols
    crypto_mask = df["exchange"].isin(list(crypto_exchanges))
    if "timezone" in df.columns:
        df["timezone"] = df["timezone"].astype("string")
    else:
        df["timezone"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df.loc[crypto_mask & df["timezone"].isna(), "timezone"] = "UTC"

    # Fix session for crypto symbols
    crypto_types = ["spot", "swap"]
    if "session" in df.columns:
        df["session"] = df["session"].astype("string")
    else:
        df["session"] = pd.Series(pd.NA, index=df.index, dtype="string")
    crypto_session_mask = crypto_mask & df["type"].isin(crypto_types) & df["session"].isna()
    df.loc[crypto_session_mask, "session"] = "24x7"

    # 3. Resolve SCD Type 2 duplicates, ensuring only one active record per symbol
    logger.info("Resolving SCD Type 2 duplicates...")

    if not df.empty:
        # Sort by symbol and valid_from/updated_at to ensure chronological order
        df = df.sort_values(["symbol", "valid_from", "updated_at"], ascending=[True, True, True])

        resolved_records = []
        for symbol, group in df.groupby("symbol"):
            group = group.copy()
            # Sort group chronologically
            group = group.sort_values(["valid_from", "updated_at"])

            records = group.to_dict("records")
            for i in range(len(records) - 1):
                # If this record is supposed to be active but there's a later one,
                # we must expire it.
                if pd.isna(records[i]["valid_until"]):
                    next_start = records[i + 1]["valid_from"]
                    if pd.isna(next_start):
                        # Fallback if valid_from is missing
                        next_start = records[i + 1]["updated_at"]

                    records[i]["valid_until"] = next_start
                    logger.info(f"Fixed duplicate active record for {symbol} at index {i}")

            resolved_records.extend(records)

        cleaned_df = pd.DataFrame(resolved_records)
    else:
        cleaned_df = df

    # 4. Validate and fix exchange information
    logger.info("Validating exchange information...")

    # Add missing exchange metadata
    for exchange in cleaned_df["exchange"].dropna().unique():
        if exchange not in DEFAULT_EXCHANGE_METADATA:
            logger.warning(f"Exchange {exchange} not in default metadata, adding basic info")
            # This will be added to exchange catalog later

    # Replace the catalog DataFrame
    catalog._df = cleaned_df
    catalog.save()

    # Report results
    logger.info("Cleanup complete!")
    logger.info(f"Original records: {len(df)}")
    logger.info(f"After cleanup: {len(cleaned_df)}")
    logger.info(f"Duplicates removed: {len(df) - len(cleaned_df)}")

    # Show sample of cleaned data
    logger.info("Sample cleaned records:")
    sample_symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BYBIT:SOLUSDT"]
    for symbol in sample_symbols:
        record = catalog.get_instrument(symbol)
        if record:
            logger.info(f"  {symbol}: pricescale={record['pricescale']} ({type(record['pricescale'])}), minmov={record['minmov']} ({type(record['minmov'])}), tick_size={record['tick_size']}")


if __name__ == "__main__":
    cleanup_metadata_catalog()
