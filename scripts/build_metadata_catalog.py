import argparse
import json
import logging
import os
import shutil
from pathlib import Path

import pandas as pd

from tradingview_scraper.symbols.stream.fetching import (
    _validate_symbol_record_for_upsert,
    fetch_tv_metadata,
)
from tradingview_scraper.symbols.stream.metadata import DEFAULT_EXCHANGE_METADATA, ExchangeCatalog, MetadataCatalog

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("build_metadata_catalog")


def main():
    parser = argparse.ArgumentParser(description="Build/Update Metadata Catalog")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--symbols", nargs="+", help="List of symbols to process")
    group.add_argument("--from-catalog", action="store_true", help="Refresh all active symbols from existing symbols.parquet")
    group.add_argument("--candidates-file", type=str, help="Refresh specific symbols from a JSON candidates file")

    parser.add_argument("--catalog-path", type=str, default="data/lakehouse/symbols.parquet")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    target_symbols = []
    if args.symbols:
        target_symbols = args.symbols
    elif args.candidates_file:
        if os.path.exists(args.candidates_file):
            with open(args.candidates_file, "r") as f:
                cands = json.load(f)

            # Polymorphic handling: List[str] or List[Dict]
            if isinstance(cands, list):
                if not cands:
                    target_symbols = []
                elif isinstance(cands[0], str):
                    target_symbols = sorted(list(set(cands)))
                elif isinstance(cands[0], dict):
                    target_symbols = sorted({c.get("symbol") for c in cands if c.get("symbol")})
                else:
                    logger.warning(f"Unknown format in {args.candidates_file}. Expected list of strings or objects with 'symbol' key.")

            logger.info(f"Loaded {len(target_symbols)} symbols from {args.candidates_file}")
        else:
            logger.error(f"Candidates file not found: {args.candidates_file}")
            return
    elif args.from_catalog:
        if os.path.exists(args.catalog_path):
            try:
                df = pd.read_parquet(args.catalog_path)
                if "active" in df.columns:
                    df = df[df["active"] == True]
                # Use explicit cast to Series to satisfy type checker
                symbol_series = pd.Series(df["symbol"])
                target_symbols = sorted(symbol_series.dropna().unique().tolist())
                logger.info(f"Loaded {len(target_symbols)} symbols from catalog")
            except Exception as e:
                logger.error(f"Failed to read catalog: {e}")
                return
        else:
            logger.error(f"Catalog not found at {args.catalog_path}")
            return

    if not target_symbols:
        logger.error("No target symbols resolved.")
        return

    # Backup existing catalog
    if os.path.exists(args.catalog_path):
        backup_path = args.catalog_path + ".bak"
        try:
            shutil.copy2(args.catalog_path, backup_path)
            logger.info(f"Backed up catalog to {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")

    catalog_data = fetch_tv_metadata(target_symbols, max_workers=args.workers)

    if catalog_data:
        # Initialize catalog pointing to the correct directory
        catalog_file = Path(args.catalog_path)
        base_path = catalog_file.parent
        catalog = MetadataCatalog(base_path=base_path)

        validated_data = [r for r in catalog_data if _validate_symbol_record_for_upsert(r)]

        if validated_data:
            catalog.upsert_symbols(validated_data)
            logger.info(f"Upserted {len(validated_data)} symbols to catalog.")

        ex_catalog = ExchangeCatalog(base_path=base_path)
        exchanges = {r["exchange"] for r in catalog_data if r.get("exchange")}
        for ex in exchanges:
            defaults = DEFAULT_EXCHANGE_METADATA.get(ex, {})
            ex_catalog.upsert_exchange({"exchange": ex, "timezone": defaults.get("timezone", "UTC"), "is_crypto": defaults.get("is_crypto", False), "country": defaults.get("country", "Global")})
        logger.info("Catalog update complete.")


if __name__ == "__main__":
    main()
