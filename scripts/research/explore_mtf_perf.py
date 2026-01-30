import argparse
import logging

from tradingview_scraper.symbols.overview import Overview

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("explore_mtf_perf")


def explore_mtf_perf(symbol: str = "BINANCE:BTCUSDT"):
    overview = Overview()

    # Fields to test
    # Standard perfs + potential long-term perfs
    request_fields = ["Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.Y", "Perf.YTD", "Perf.3Y", "Perf.5Y", "Perf.All"]

    logger.info(f"Requesting {len(request_fields)} fields for {symbol}...")

    res = overview.get_symbol_overview(symbol, fields=request_fields)

    if res["status"] == "success":
        data = res["data"]
        print(f"\nResults for {symbol}:")
        for field in request_fields:
            val = data.get(field)
            if val is not None:
                print(f"{field}: {val}")
            else:
                print(f"{field}: None")
    else:
        logger.error(f"Failed: {res.get('error')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BINANCE:BTCUSDT")
    args = parser.parse_args()
    explore_mtf_perf(args.symbol)
