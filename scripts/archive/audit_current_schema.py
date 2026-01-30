import json

from tradingview_scraper.symbols.overview import Overview
from tradingview_scraper.symbols.stream import Streamer


def audit_schema():
    print("[INFO] Auditing current data schemas...")

    # 1. Fetch OHLCV Schema
    streamer = Streamer(export_result=False)
    ohlc_data = {}
    try:
        # Fetch just a few candles to inspect structure
        res = streamer.stream("BINANCE", "BTCUSDT", timeframe="1h", numb_price_candles=5, auto_close=True)
        if "ohlc" in res and len(res["ohlc"]) > 0:
            ohlc_data = res["ohlc"][0]
            print("  [SUCCESS] Captured OHLCV sample.")
    except Exception as e:
        print(f"  [ERROR] OHLCV fetch failed: {e}")

    # 2. Fetch Overview/Metadata Schema
    overview = Overview()
    meta_data = {}
    try:
        res = overview.get_symbol_overview("BINANCE:BTCUSDT")
        if res["status"] == "success":
            meta_data = res["data"]
            print("  [SUCCESS] Captured Overview sample.")
    except Exception as e:
        print(f"  [ERROR] Overview fetch failed: {e}")

    final_report = {"OHLCV_Sample": ohlc_data, "Overview_Sample": meta_data}

    with open("docs/research/current_schema_audit.json", "w") as f:
        json.dump(final_report, f, indent=2)

    print("[DONE] Schema audit saved to docs/research/current_schema_audit.json")


if __name__ == "__main__":
    audit_schema()
