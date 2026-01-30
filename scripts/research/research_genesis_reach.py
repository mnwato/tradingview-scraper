import time
from datetime import datetime

import pandas as pd

from tradingview_scraper.symbols.stream import Streamer


def test_genesis_reach():
    # Test very large counts to see where TV cuts us off
    depth_tests = [("1d", 5000), ("1h", 10000), ("1m", 10000)]

    print("\n" + "=" * 100)
    print("GENESIS REACH TEST (MAX DEPTH) - FRESH INSTANCES")
    print("=" * 100)

    results = []
    for tf, count in depth_tests:
        print(f"\n>>> Requesting {count} candles for {tf} <<<")
        try:
            # CREATE FRESH STREAMER PER CALL
            streamer = Streamer(export_result=True)
            start_time = time.time()
            res = streamer.stream("BINANCE", "BTCUSDT", timeframe=tf, numb_price_candles=count, auto_close=True)
            elapsed = time.time() - start_time

            candles = res.get("ohlc", [])
            received = len(candles)

            if received > 0:
                first = datetime.fromtimestamp(candles[0]["timestamp"])
                last = datetime.fromtimestamp(candles[-1]["timestamp"])
                results.append({"TF": tf, "Req": count, "Rec": received, "Oldest": first.strftime("%Y-%m-%d %H:%M"), "Newest": last.strftime("%Y-%m-%d %H:%M"), "Time": f"{elapsed:.2f}s"})
                print(f"  [SUCCESS] Oldest reachable: {first}")
            else:
                print(f"  [FAILED] No data returned for {tf}")
        except Exception as e:
            print(f"  [ERROR] {e}")

        time.sleep(2)

    df_res = pd.DataFrame(results)
    print("\n" + df_res.to_string(index=False))


if __name__ == "__main__":
    test_genesis_reach()
