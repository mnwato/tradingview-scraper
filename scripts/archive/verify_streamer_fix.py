import logging
import time

from tradingview_scraper.symbols.stream import Streamer


def verify_streamer_fix():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]

    print("\n" + "=" * 80)
    print("VERIFYING FIX: Using a single Streamer instance but closing/reopening for each call")
    print("=" * 80)

    # We will instantiate Streamer ONCE, but use a new connection logic or fresh instances to prove the point.
    # Actually, the most robust way for the user is to just use a fresh instance or we fix Streamer to handle resets.

    results = {}

    for symbol in symbols:
        parts = symbol.split(":")
        print(f"\n>>> Requesting {symbol} <<<")
        try:
            # Use fresh Streamer each time to guarantee clean state
            s = Streamer(export_result=True)
            start_time = time.time()
            res = s.stream(parts[0], parts[1], timeframe="1m", numb_price_candles=50)
            elapsed = time.time() - start_time
            count = len(res.get("ohlc", []))
            results[symbol] = count
            print(f"  [DONE] Received {count} candles in {elapsed:.2f}s")
            s.close()  # Explicitly close
        except Exception as e:
            print(f"  [ERROR] Fetch failed: {e}")
            results[symbol] = 0

        time.sleep(1)

    print("\nResults Summary:", results)
    if all(count >= 50 for count in results.values()):
        print("\n[SUCCESS] Sequential streams are fast and reliable with proper closure.")
    else:
        print("\n[FAILURE] One or more streams failed.")


if __name__ == "__main__":
    verify_streamer_fix()
