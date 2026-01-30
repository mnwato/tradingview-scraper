import json
import logging
from datetime import datetime, timedelta

from tradingview_scraper.symbols.stream.loader import DataLoader


def demo_backtest_loader():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    loader = DataLoader()

    # Range: Last 3 days
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=3)
    interval = "15m"

    symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]

    backtest_data = {}

    for symbol in symbols:
        print(f"\n>>> Loading backtest data for {symbol} ({interval}) <<<")
        data = loader.load(symbol, start_dt, end_dt, interval=interval)

        if data:
            first_ts = datetime.fromtimestamp(data[0]["timestamp"])
            last_ts = datetime.fromtimestamp(data[-1]["timestamp"])
            print(f"  [SUCCESS] Loaded {len(data)} candles.")
            print(f"  Range: {first_ts} to {last_ts}")
            backtest_data[symbol] = data
        else:
            print(f"  [FAILURE] No data returned for {symbol}")

    output_file = "export/backtest_demo_dataset.json"
    with open(output_file, "w") as f:
        json.dump(backtest_data, f, indent=2)

    print(f"\n[DONE] Demo dataset saved to {output_file}")


if __name__ == "__main__":
    demo_backtest_loader()
