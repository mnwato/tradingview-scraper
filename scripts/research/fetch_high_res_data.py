import json
import logging
import time

from tradingview_scraper.settings import get_settings
from tradingview_scraper.symbols.stream import Streamer
from tradingview_scraper.symbols.technicals import Indicators


def fetch_high_res_data():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    target_symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT"]
    print(f"[INFO] Fetching high-resolution (1m) data for: {target_symbols}")

    ind_scraper = Indicators()
    target_indicators = ["RSI", "MACD.macd", "EMA50", "EMA200", "ADX"]

    final_data = {}

    for full_symbol in target_symbols:
        parts = full_symbol.split(":")
        exchange = parts[0]
        symbol = parts[1]

        print(f"\n>>> Processing {full_symbol} (1m) <<<")
        final_data[full_symbol] = {"1m_ohlcv": [], "1m_indicators": {}}

        # A. Fetch 500 candles of 1m data with auto_close=True
        try:
            # We create a fresh streamer or use auto_close to ensure clean state
            streamer = Streamer(export_result=True)
            start_fetch = time.time()
            print("  Fetching 500 candles (1m)...")
            ohlc_res = streamer.stream(exchange, symbol, timeframe="1m", numb_price_candles=500, auto_close=True)
            elapsed = time.time() - start_fetch

            candles = ohlc_res.get("ohlc", [])
            final_data[full_symbol]["1m_ohlcv"] = candles
            print(f"  [SUCCESS] Received {len(candles)} candles in {elapsed:.2f}s")
        except Exception as e:
            print(f"  [ERROR] OHLC fetch failed: {e}")

        # B. Fetch Technical Indicators Snapshot (1m)
        try:
            print("  Fetching indicators snapshot (1m)...")
            tech_res = ind_scraper.scrape(exchange, symbol, timeframe="1m", indicators=target_indicators)
            if tech_res["status"] == "success":
                final_data[full_symbol]["1m_indicators"] = tech_res["data"]
                print("  [SUCCESS] Indicators captured.")
        except Exception as e:
            print(f"  [ERROR] Indicators fetch failed: {e}")

        time.sleep(1)

    settings = get_settings()
    output_file = settings.export_dir / "high_res_research_bundle.json"
    with open(output_file, "w") as f:
        json.dump(final_data, f, indent=2)

    print(f"\n[DONE] High-res data bundle saved to {output_file}")


if __name__ == "__main__":
    fetch_high_res_data()
