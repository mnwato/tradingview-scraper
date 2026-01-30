import json

from tradingview_scraper.symbols.screener import Screener


def inspect_america_fields():
    screener = Screener()
    columns = [
        "name",
        "close",
        "volume",
        "Value.Traded",
        "market_cap_basic",
        "change",
    ]

    print(f"Requesting columns for america: {columns}")

    # Search for Apple
    filters = [{"left": "name", "operation": "equal", "right": "AAPL"}]

    try:
        result = screener.screen(market="america", filters=filters, columns=columns, limit=1)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    inspect_america_fields()
