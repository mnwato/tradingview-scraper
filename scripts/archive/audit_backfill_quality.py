#!/usr/bin/env python3
"""
Audit the quality of backfilled OHLCV data.
"""

import logging
import os

import pandas as pd

from scripts.verify_portfolio_symbols import load_json_symbols

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audit_backfill")


def audit_backfill():
    base_path = "data/lakehouse"
    files = ["portfolio_barbell.json", "portfolio_optimized.json"]

    symbols = set()
    for filename in files:
        filepath = os.path.join(base_path, filename)
        if os.path.exists(filepath):
            symbols.update(load_json_symbols(filepath))

    logger.info(f"Auditing backfill quality for {len(symbols)} symbols...")

    stats = []

    for symbol in symbols:
        filename = f"{symbol.replace(':', '_')}_1d.parquet"
        filepath = os.path.join(base_path, filename)

        if os.path.exists(filepath):
            try:
                df = pd.read_parquet(filepath)
                row_count = len(df)
                if row_count > 0:
                    # Assuming 'datetime' or 'time' column exists, or index is time
                    # Let's inspect columns if needed, but usually it's standard
                    # Common columns: open, high, low, close, volume, time/datetime

                    # Find time column
                    time_col = None
                    for col in ["time", "datetime", "date", "timestamp"]:
                        if col in df.columns:
                            time_col = col
                            break

                    if time_col:
                        last_date = df[time_col].max()
                        first_date = df[time_col].min()
                    else:
                        last_date = "Unknown"
                        first_date = "Unknown"

                    stats.append({"symbol": symbol, "rows": row_count, "start": first_date, "end": last_date, "status": "OK"})
                else:
                    stats.append({"symbol": symbol, "rows": 0, "start": None, "end": None, "status": "EMPTY"})
            except Exception as e:
                stats.append({"symbol": symbol, "rows": 0, "start": None, "end": None, "status": f"ERROR: {str(e)}"})
        else:
            stats.append({"symbol": symbol, "rows": 0, "start": None, "end": None, "status": "MISSING"})

    # Report
    df_stats = pd.DataFrame(stats)
    print("\n=== BACKFILL QUALITY REPORT ===")
    print(f"Total Symbols: {len(symbols)}")
    print(f"Empty/Missing: {len(df_stats[df_stats['rows'] == 0])}")

    # Check for stale data (e.g. older than 7 days)
    # This requires converting 'end' to datetime if it's not
    # For now just printing head/tail by row count

    print("\nTop 10 Symbols by Row Count:")
    print(df_stats.sort_values("rows", ascending=False).head(10).to_string(index=False))

    print("\nBottom 10 Symbols by Row Count:")
    print(df_stats.sort_values("rows").head(10).to_string(index=False))

    empty_df = df_stats[df_stats["rows"] == 0]
    if not empty_df.empty:
        print("\n⚠️ Empty or Missing Files:")
        print(empty_df["symbol"].to_string(index=False))

        # Save empty symbols for re-fetching
        with open("empty_backfill_symbols.txt", "w") as f:
            for sym in empty_df["symbol"]:
                f.write(f"{sym}\n")
        logger.info("Empty symbols saved to empty_backfill_symbols.txt")


if __name__ == "__main__":
    audit_backfill()
