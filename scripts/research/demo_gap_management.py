import logging
from datetime import datetime

import pandas as pd

from tradingview_scraper.symbols.stream.persistent_loader import PersistentDataLoader


def demo_gap_management():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    loader = PersistentDataLoader()
    symbol = "BINANCE:BTCUSDT"
    interval = "1m"

    # 1. Check current state
    print("\n" + "=" * 80)
    print(f"GAP MANAGEMENT DEMO: {symbol} ({interval})")
    print("=" * 80)

    df_initial = loader.storage.load_candles(symbol, interval)
    print(f"Initial candle count: {len(df_initial)}")

    # 2. MANUALLY INTRODUCE A GAP
    # We delete middle 100 candles
    if len(df_initial) > 500:
        print("\n[STEP 1] Manually introducing a gap by deleting 100 candles...")
        df_gap = pd.concat([df_initial.iloc[:200], df_initial.iloc[300:]])

        # Save the gapped data back
        file_path = loader.storage._get_path(symbol, interval)
        df_gap.to_parquet(file_path, index=False)

        # 3. DETECT GAP
        print("\n[STEP 2] Detecting gaps...")
        gaps = loader.storage.detect_gaps(symbol, interval)
        for s, e in gaps:
            print(f"  Detected Gap: {datetime.fromtimestamp(s)} to {datetime.fromtimestamp(e)}")

        # 4. REPAIR GAP
        print("\n[STEP 3] Running repair...")
        filled = loader.repair(symbol, interval)
        print(f"  Repair complete. Filled {filled} candles.")

        # 5. FINAL VERIFY
        df_final = loader.storage.load_candles(symbol, interval)
        print(f"\nFinal candle count: {len(df_final)}")
        gaps_final = loader.storage.detect_gaps(symbol, interval)
        if not gaps_final:
            print("[SUCCESS] All gaps repaired!")
        else:
            print(f"[REMAINING GAPS] {len(gaps_final)} gaps still exist.")
    else:
        print("[SKIP] Not enough data to introduce a gap safely. Run run_lakehouse_sync.py first.")


if __name__ == "__main__":
    demo_gap_management()
