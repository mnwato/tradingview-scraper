import logging
import time

from tradingview_scraper.symbols.stream import Streamer


def verify_sequential_streams():
    # Set logging to capture the detailed flow
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # We will use two different high-liquidity symbols
    symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]

    # CASE 1: Reuse same Streamer instance
    print("\n" + "=" * 80)
    print("CASE 1: Reusing the same Streamer instance for sequential calls")
    print("=" * 80)

    streamer_shared = Streamer(export_result=True)
    results_shared = {}

    for symbol in symbols:
        parts = symbol.split(":")
        print(f"\n>>> Requesting {symbol} (shared instance) <<<")
        try:
            start_time = time.time()
            # Fetching 50 candles to ensure a substantial packet flow
            res = streamer_shared.stream(parts[0], parts[1], timeframe="1m", numb_price_candles=50)
            elapsed = time.time() - start_time
            count = len(res.get("ohlc", []))
            results_shared[symbol] = count
            print(f"  [DONE] Received {count} candles in {elapsed:.2f}s")
        except Exception as e:
            print(f"  [ERROR] Fetch failed: {e}")
            results_shared[symbol] = 0

        time.sleep(2)  # Cooldown

    # CASE 2: New Streamer instance per call (Fresh connection)
    print("\n" + "=" * 80)
    print("CASE 2: Fresh Streamer instance per call")
    print("=" * 80)

    results_fresh = {}
    for symbol in symbols:
        parts = symbol.split(":")
        print(f"\n>>> Requesting {symbol} (fresh instance) <<<")
        try:
            streamer_fresh = Streamer(export_result=True)
            start_time = time.time()
            res = streamer_fresh.stream(parts[0], parts[1], timeframe="1m", numb_price_candles=50)
            elapsed = time.time() - start_time
            count = len(res.get("ohlc", []))
            results_fresh[symbol] = count
            print(f"  [DONE] Received {count} candles in {elapsed:.2f}s")
        except Exception as e:
            print(f"  [ERROR] Fetch failed: {e}")
            results_fresh[symbol] = 0

        time.sleep(2)

    print("\n" + "=" * 80)
    print("FINAL VERIFICATION SUMMARY")
    print("=" * 80)
    print("Shared Streamer Results:", results_shared)
    print("Fresh Streamer Results: ", results_fresh)

    if results_shared[symbols[1]] == 0 and results_fresh[symbols[1]] > 0:
        print("\n[ISSUE DETECTED] Reusing Streamer instance caused the second request to fail or timeout.")
    else:
        print("\n[INFO] Both symbols fetched in both cases, but check logs for data overlap or weirdness.")


if __name__ == "__main__":
    verify_sequential_streams()
