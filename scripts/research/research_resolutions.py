import json
import time
from datetime import datetime

import pandas as pd

from tradingview_scraper.symbols.stream import Streamer


def research_resolutions():
    streamer = Streamer(export_result=True)

    # Comprehensive list of timeframes to probe
    # Format: (display_name, internal_code)
    resolutions_to_test = [
        # Seconds (Experimental)
        ("1s", "1S"),
        ("5s", "5S"),
        ("15s", "15S"),
        ("30s", "30S"),
        # Minutes
        ("1m", "1"),
        ("2m", "2"),
        ("3m", "3"),
        ("5m", "5"),
        ("15m", "15"),
        ("30m", "30"),
        ("45m", "45"),
        # Hours
        ("1h", "60"),
        ("2h", "120"),
        ("3h", "180"),
        ("4h", "240"),
        ("12h", "720"),
        # Days/Weeks/Months
        ("1d", "1D"),
        ("1w", "1W"),
        ("1M", "1M"),
    ]

    print("\n" + "=" * 100)
    print("TRADINGVIEW RESOLUTION DISCOVERY RESEARCH")
    print("=" * 100)

    results = []

    for display, code in resolutions_to_test:
        print(f"\n>>> Probing Resolution: {display} (Code: {code}) <<<")
        try:
            # We bypass the internal mapping by temporarily patching Streamer or using a custom call
            # For this test, we'll modify the internal _add_symbol_to_sessions to use the raw code

            from tradingview_scraper.symbols.stream import StreamHandler

            # Helper to create a manual stream session with the raw code
            def fetch_raw_code(exchange, symbol, raw_code):
                sh = StreamHandler(streamer.ws_url, streamer.websocket_jwt_token)
                qs = sh.quote_session
                cs = sh.chart_session

                resolve_symbol = json.dumps({"adjustment": "splits", "symbol": f"{exchange}:{symbol}"})
                sh.send_message("quote_add_symbols", [qs, f"={resolve_symbol}"])
                sh.send_message("resolve_symbol", [cs, "sds_sym_1", f"={resolve_symbol}"])
                # The 5th param is the resolution code
                sh.send_message("create_series", [cs, "sds_1", "s1", "sds_sym_1", raw_code, 100, ""])
                sh.send_message("quote_fast_symbols", [qs, f"{exchange}:{symbol}"])

                # Use streamer's get_data logic to grab one packet
                ohlc_data = []
                start = time.time()
                while time.time() - start < 10:  # 10s timeout
                    result = sh.ws.recv()
                    # Basic heartbeat/packet split logic
                    if "~m~" in result:
                        parts = [x for x in result.split("~m~") if x and not x.isdigit()]
                        for p in parts:
                            if "timescale_update" in p:
                                try:
                                    js = json.loads(p)
                                    ohlc_data = streamer._extract_ohlc_from_stream(js)
                                    if ohlc_data:
                                        break
                                except (json.JSONDecodeError, KeyError, TypeError):
                                    continue
                    if ohlc_data:
                        break

                sh.close()
                return ohlc_data

            start_time = time.time()
            candles = fetch_raw_code("BINANCE", "BTCUSDT", code)
            elapsed = time.time() - start_time

            received = len(candles)
            if received > 0:
                first = datetime.fromtimestamp(candles[0]["timestamp"])
                last = datetime.fromtimestamp(candles[-1]["timestamp"])
                results.append(
                    {
                        "Display": display,
                        "Code": code,
                        "Status": "SUPPORTED",
                        "Count": received,
                        "Reach": f"{first.strftime('%Y-%m-%d %H:%M')} to {last.strftime('%Y-%m-%d %H:%M')}",
                        "Elapsed": f"{elapsed:.2f}s",
                    }
                )
                print(f"  [SUCCESS] Received {received} candles.")
            else:
                results.append({"Display": display, "Code": code, "Status": "UNSUPPORTED/EMPTY", "Count": 0, "Reach": "N/A", "Elapsed": f"{elapsed:.2f}s"})
                print(f"  [WARNING] No data returned for code: {code}")

        except Exception as e:
            results.append({"Display": display, "Code": code, "Status": f"ERROR: {str(e)[:30]}", "Count": 0, "Reach": "N/A", "Elapsed": "N/A"})
            print(f"  [ERROR] {e}")

        time.sleep(1)

    df = pd.DataFrame(results)
    print("\n" + "=" * 120)
    print("RESOLUTION MATRIX SUMMARY")
    print("=" * 120)
    print(df.to_string(index=False))

    output_file = "docs/research/resolution_discovery_matrix.json"
    df.to_json(output_file, orient="records", indent=2)
    print(f"\n[DONE] Research results saved to {output_file}")


if __name__ == "__main__":
    research_resolutions()
