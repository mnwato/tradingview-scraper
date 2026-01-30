import json
import time

from tradingview_scraper.settings import get_settings
from tradingview_scraper.symbols.stream import Streamer
from tradingview_scraper.symbols.technicals import Indicators


def research_historical_technicals():
    settings = get_settings()
    mapping_file = settings.export_dir / "multi_quote_mapping.json"
    if not mapping_file.exists():
        print(f"[ERROR] Mapping file {mapping_file} not found.")
        return

    with open(mapping_file, "r") as f:
        mapping = json.load(f)

    # Research top 3 primaries
    target_primaries = list(mapping.keys())[:3]
    print(f"[INFO] Researching historical data and indicators for: {target_primaries}")

    # Note: Streamer with export_result=True returns a dictionary
    # but with export_result=False, it returns a generator from get_data().
    # Let's use export_result=True to get the final bundle.
    streamer = Streamer(export_result=True)
    ind_scraper = Indicators()

    target_indicators = ["RSI", "MACD.macd", "EMA50", "EMA200", "ADX"]
    research_results = []

    for full_symbol in target_primaries:
        parts = full_symbol.split(":")
        exchange = parts[0]
        symbol = parts[1]

        print(f"\n>>> Processing {full_symbol} <<<")
        entry = {"symbol": full_symbol, "historical": {}, "technicals": {}}

        try:
            print("  Fetching 100 candles (1h)...")
            # Set numb_price_candles to a smaller number for faster research
            # When export_result=True, stream() returns {"ohlc": [...], "indicator": {...}}
            ohlc_res = streamer.stream(exchange, symbol, timeframe="1h", numb_price_candles=100)

            candles = ohlc_res.get("ohlc", [])
            entry["historical"]["1h_count"] = len(candles)
            if candles:
                entry["historical"]["1h_sample"] = candles[0]
        except Exception as e:
            print(f"  [ERROR] OHLC fetch failed: {e}")

        try:
            print("  Fetching indicators snapshot (1h)...")
            tech_res = ind_scraper.scrape(exchange, symbol, timeframe="1h", indicators=target_indicators)
            if tech_res["status"] == "success":
                entry["technicals"] = tech_res["data"]
        except Exception as e:
            print(f"  [ERROR] Indicators fetch failed: {e}")

        research_results.append(entry)
        time.sleep(2)

    # Use docs dir from relative path or settings if we had one?
    # Current behavior is relative "docs/"
    output_file = "docs/historical_technicals_summary.json"
    with open(output_file, "w") as f:
        json.dump(research_results, f, indent=2)

    print(f"\n[DONE] Research complete. Summary saved to {output_file}")


if __name__ == "__main__":
    research_historical_technicals()
