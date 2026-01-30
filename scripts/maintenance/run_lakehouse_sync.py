import logging
from datetime import datetime

from tradingview_scraper.symbols.stream.persistent_loader import PersistentDataLoader


def run_lakehouse_sync():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # 1. Initialize persistent loader
    loader = PersistentDataLoader(lakehouse_path="data/lakehouse")

    # 2. Hybrid ITD Strategy demonstration for BTCUSDT
    symbol = "BINANCE:BTCUSDT"

    print("\n" + "=" * 80)
    print(f"HYBRID LAKEHOUSE SYNC: {symbol}")
    print("=" * 80)

    # A. Macro Sync (1d) - Reach back to inception (2017)
    print("\n[PHASE A] Syncing Macro History (1d)...")
    loader.sync(symbol, interval="1d", depth=5000)

    # B. Structural Sync (1h) - Reach back ~1 year
    print("\n[PHASE B] Syncing Structural History (1h)...")
    loader.sync(symbol, interval="1h", depth=8500)

    # C. High-Res Forward Accumulation (1m) - Reach back ~6 days
    print("\n[PHASE C] Syncing High-Res Buffer (1m)...")
    loader.sync(symbol, interval="1m", depth=8500)

    # 3. Final Audit of Lakehouse
    print("\n" + "=" * 80)
    print("LAKEHOUSE AUDIT")
    print("=" * 80)

    for interval in ["1d", "1h", "1m"]:
        df = loader.storage.load_candles(symbol, interval)
        if not df.empty:
            first = datetime.fromtimestamp(df["timestamp"].min())
            last = datetime.fromtimestamp(df["timestamp"].max())
            print(f"  {interval:<3} | Count: {len(df):<6} | Range: {first} to {last}")
        else:
            print(f"  {interval:<3} | NO DATA")


if __name__ == "__main__":
    run_lakehouse_sync()
