from datetime import datetime

from tradingview_scraper.symbols.stream import Streamer


def verify():
    # Test ACTUSDT (New) and BTCUSDT (Old)
    symbols = [("BINANCE", "ACTUSDT"), ("BINANCE", "BTCUSDT")]

    for ex, sym in symbols:
        print(f"Checking {ex}:{sym}...")
        try:
            streamer = Streamer(export_result=True)
            # Request 1M candles (monthly) to find start quickly?
            # Or 1D and ask for max?
            # 'numb_price_candles' controls how far back?
            # If we ask for 10,000 daily candles, we get genesis.

            res = streamer.stream(ex, sym, timeframe="1D", numb_price_candles=10000, auto_close=True)
            candles = res.get("ohlc", [])
            if candles:
                first_ts = candles[0]["timestamp"]
                first_date = datetime.fromtimestamp(first_ts)
                print(f"  Genesis: {first_date}")
            else:
                print("  No candles returned")
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    verify()
