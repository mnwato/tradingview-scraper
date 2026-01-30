import json

from tradingview_scraper.symbols.screener import Screener


def inspect_america_sorting():
    screener = Screener()
    columns = ["name", "close", "market_cap_basic"]
    filters = [{"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE"]}]

    try:
        print("Testing sort_by market_cap_basic...")
        result = screener.screen(market="america", filters=filters, columns=columns, sort_by="market_cap_basic", sort_order="desc", limit=1)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    inspect_america_sorting()
