from tradingview_scraper.symbols.screener import Screener


def inspect_fields():
    screener = Screener()
    # Likely candidates for start date
    columns = [
        "name",
        "close",
        "volume",
        "Value.Traded",
        "market_cap_calc",
        "market_cap_basic",
        "change",
        "ADX",
        "Recommend.All",
        "Volatility.D",
        "Volatility.W",
        "Volatility.M",
        "Perf.W",
        "Perf.1M",
        "Perf.3M",
        "volume_change",
        "type",
    ]

    # Try one by one for risky fields? No, batch.

    print(f"Requesting columns: {columns}")

    filters = [{"left": "exchange", "operation": "equal", "right": "BINANCE"}, {"left": "Value.Traded", "operation": "greater", "right": 50000000}]
    try:
        result = screener.screen(market="crypto", filters=filters, columns=["name", "type", "Value.Traded"], limit=20)

        if result["status"] == "success" and result["data"]:
            for item in result["data"]:
                print(f"{item['symbol']} | type: {item.get('type')} | volume: {item.get('Value.Traded'):,.0f}")
        else:
            print("Failed:", result)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    inspect_fields()
