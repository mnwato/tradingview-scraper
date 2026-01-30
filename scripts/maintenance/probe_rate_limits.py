import time

import pandas as pd
import requests

from tradingview_scraper.symbols.utils import generate_user_agent


def probe_screener_limit():
    url = "https://scanner.tradingview.com/symbol?symbol=BINANCE:BTCUSDT&fields=close"
    headers = {"user-agent": generate_user_agent()}

    print("\n" + "=" * 80)
    print("PROBING SCREENER REST API LIMITS")
    print("=" * 80)

    results = []

    # Send 100 requests as fast as possible
    for i in range(100):
        start = time.time()
        try:
            res = requests.get(url, headers=headers, timeout=5)
            elapsed = time.time() - start
            results.append({"Req": i + 1, "Status": res.status_code, "Elapsed": f"{elapsed:.2f}s"})
            if res.status_code != 200:
                print(f"  [SIGNAL] Request {i + 1} returned {res.status_code}")
                # If we get 429, we should stop and see how long it lasts
                if res.status_code == 429:
                    break
        except Exception as e:
            print(f"  [ERROR] Request {i + 1} failed: {e}")
            break

    df = pd.DataFrame(results)
    print("\nProbe Results (First 5 and Last 5):")
    print(df.head())
    print("...")
    print(df.tail())

    unique_statuses = df["Status"].unique()
    print(f"\nUnique Status Codes Encountered: {unique_statuses}")


if __name__ == "__main__":
    probe_screener_limit()
