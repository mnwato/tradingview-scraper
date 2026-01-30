#!/usr/bin/env python3
"""
Audit symbol age precisely by fetching the first candle via Streamer.
Updates MetadataCatalog with 'genesis_ts' field.
"""

import logging
import time
from datetime import datetime

from tradingview_scraper.symbols.stream import Streamer
from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audit_age_precise")


def audit_ages_precise():
    catalog = MetadataCatalog()
    df = catalog._df

    # Initialize genesis_ts if not present
    if "genesis_ts" not in df.columns:
        df["genesis_ts"] = None

    # Get active symbols without genesis_ts
    active_mask = df["valid_until"].isna()
    todo_mask = active_mask & df["genesis_ts"].isna()
    symbols_to_check = df[todo_mask]["symbol"].tolist()

    logger.info(f"Checking genesis for {len(symbols_to_check)} symbols...")

    count = 0
    for sym in symbols_to_check:
        count += 1
        exchange = sym.split(":")[0]
        ticker = sym.split(":")[1]

        logger.info(f"[{count}/{len(symbols_to_check)}] Checking {sym}...")

        try:
            # Use aggressive timeouts to fail fast if data ends (genesis reached)
            streamer = Streamer(export_result=True, idle_packet_limit=3, idle_timeout_seconds=5.0)

            res = streamer.stream(exchange=exchange, symbol=ticker, timeframe="1d", numb_price_candles=5000, auto_close=True)

            candles = res.get("ohlc", [])
            if candles:
                first_ts = candles[0]["timestamp"]
                genesis_date = datetime.fromtimestamp(first_ts)
                logger.info(f"  Found genesis: {genesis_date.strftime('%Y-%m-%d')} ({len(candles)} candles)")

                # Update DataFrame
                idx_mask = (df["symbol"] == sym) & (df["valid_until"].isna())
                df.loc[idx_mask, "genesis_ts"] = first_ts

                # Save periodically
                if count % 10 == 0:
                    catalog.save()
            else:
                logger.warning(f"  No candles returned for {sym}")

        except Exception as e:
            logger.error(f"  Error checking {sym}: {e}")

        # Sleep slightly
        time.sleep(0.1)

    catalog.save()
    logger.info("Precise audit complete.")


if __name__ == "__main__":
    audit_ages_precise()
