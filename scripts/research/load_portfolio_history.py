import json
import logging
import os
from datetime import datetime

from tradingview_scraper.symbols.stream.loader import DataLoader
from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

# from tradingview_scraper.symbols.utils import save_parquet_file # Assuming this exists or we use pandas directly

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_portfolio_data():
    # Load symbols
    base_path = "data/lakehouse"
    symbols = set()

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

    logger.info(f"Loading history for {len(symbols)} symbols")

    loader = DataLoader()
    catalog = MetadataCatalog()  # Ensure catalog is loaded for genesis info

    # Range: Genesis to Now
    # But calculate_candles_needed handles the start date based on genesis if we pass a very old date
    # So we can just ask for "2000-01-01" to Now, and let the loader cap it.

    start_date = datetime(2000, 1, 1)
    end_date = datetime.now()

    success_count = 0

    for i, symbol in enumerate(sorted(symbols)):
        logger.info(f"[{i + 1}/{len(symbols)}] Processing {symbol}...")

        try:
            # Check if file exists and is recent?
            # For now, let's force refresh or at least check.
            # Filename convention: EXCHANGE_SYMBOL_1d.parquet
            filename = f"{symbol.replace(':', '_')}_1d.parquet"
            filepath = os.path.join(base_path, filename)

            # Optimization: If file exists and updated recently (e.g. today), skip
            if os.path.exists(filepath):
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_time.date() == datetime.now().date():
                    logger.info(f"Skipping {symbol} - already updated today")
                    success_count += 1
                    continue

            data = loader.load(symbol, start_date, end_date, interval="1d")

            if data:
                # Save using pandas directly if utility not available or just to be sure of format
                import pandas as pd

                df = pd.DataFrame(data)
                df.to_parquet(filepath, index=False)
                logger.info(f"Saved {len(df)} rows to {filename}")
                success_count += 1
            else:
                logger.warning(f"No data returned for {symbol}")

        except Exception as e:
            logger.error(f"Failed to load {symbol}: {e}")

    logger.info(f"Completed. Successfully loaded {success_count}/{len(symbols)}")


if __name__ == "__main__":
    load_portfolio_data()
