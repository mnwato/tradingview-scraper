import time
from datetime import datetime

import pandas as pd

from tradingview_scraper.symbols.stream import Streamer


def research_loader_limits():
    # Test lookback depth across timeframes
    tests = [("1m", 1000), ("5m", 1000), ("1h", 1000), ("1d", 1000)]

    results = []

    for tf, count in tests:
        print(f"\n>>> Testing {tf} with {count} candles <<<")
        try:
            # CREATE FRESH STREAMER PER CALL to handle auto_close
            streamer = Streamer(export_result=True)
            start_time = time.time()
            res = streamer.stream("BINANCE", "BTCUSDT", timeframe=tf, numb_price_candles=count, auto_close=True)
            elapsed = time.time() - start_time

            candles = res.get("ohlc", [])
            received_count = len(candles)

            if received_count > 0:
                first_ts = candles[0]["timestamp"]
                last_ts = candles[-1]["timestamp"]

                first_dt = datetime.fromtimestamp(int(first_ts))
                last_dt = datetime.fromtimestamp(int(last_ts))

                results.append(
                    {
                        "Timeframe": tf,
                        "Requested": count,
                        "Received": received_count,
                        "First": first_dt.strftime("%Y-%m-%d %H:%M"),
                        "Last": last_dt.strftime("%Y-%m-%d %H:%M"),
                        "Elapsed": f"{elapsed:.2f}s",
                    }
                )
                print(f"  [SUCCESS] Received {received_count} candles. Range: {first_dt} to {last_dt}")
            else:
                print(f"  [WARNING] Received 0 candles for {tf}")

        except Exception as e:
            print(f"  [ERROR] Failed for {tf}: {e}")

        time.sleep(1)

    df = pd.DataFrame(results)
    print("\n" + "=" * 100)
    print("HISTORICAL DEPTH RESEARCH")
    print("=" * 100)
    print(df.to_string(index=False))

    output_file = "docs/research/historical_loader_limits.json"
    df.to_json(output_file, orient="records", date_format="iso", indent=2)
    print(f"\n[DONE] Research results saved to {output_file}")


if __name__ == "__main__":
    research_loader_limits()
