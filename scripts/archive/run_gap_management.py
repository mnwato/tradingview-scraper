import json
import logging
import os

from tradingview_scraper.symbols.stream.persistent_loader import PersistentDataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("gap_management")


def run_gap_management():
    # Load symbols
    base_path = "data/lakehouse"
    symbols = set()

    # Load from portfolio files
    try:
        with open(os.path.join(base_path, "portfolio_barbell.json")) as f:
            barbell = json.load(f)
            if "Symbol" in barbell:
                symbols.update(barbell["Symbol"].values())
    except Exception as e:
        logger.warning(f"Could not load barbell: {e}")

    try:
        with open(os.path.join(base_path, "portfolio_optimized.json")) as f:
            optimized = json.load(f)
            if "Min_Var_Weight" in optimized:
                symbols.update(optimized["Min_Var_Weight"].keys())
    except Exception as e:
        logger.warning(f"Could not load optimized: {e}")

    logger.info(f"Checking gaps for {len(symbols)} symbols")

    loader = PersistentDataLoader()
    interval = "1d"

    results = {"checked": 0, "gaps_found": 0, "gaps_filled": 0, "errors": 0}

    for i, symbol in enumerate(sorted(symbols)):
        logger.info(f"[{i + 1}/{len(symbols)}] Checking {symbol}...")
        results["checked"] += 1

        try:
            # Check for gaps first (just for logging/stats)
            gaps = loader.storage.detect_gaps(symbol, interval)
            if gaps:
                logger.info(f"  Found {len(gaps)} gaps for {symbol}")
                results["gaps_found"] += len(gaps)

                # Attempt repair
                filled = loader.repair(symbol, interval)
                logger.info(f"  Filled {filled} candles")

                if filled > 0:
                    results["gaps_filled"] += 1
            else:
                logger.info("  No gaps found.")

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            results["errors"] += 1

    logger.info("Gap management run complete.")
    logger.info(f"Summary: {results}")


if __name__ == "__main__":
    run_gap_management()
