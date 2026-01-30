from tradingview_scraper.symbols.overview import Overview


def check_fields():
    ov = Overview()
    # Check BTCUSDT (Crypto)
    print("\n--- BINANCE:BTCUSDT ---")
    res = ov.get_symbol_overview("BINANCE:BTCUSDT")
    if res.get("status") == "success":
        data = res.get("data", {})
        # Look for time/date related keys
        for k in data.keys():
            if "date" in k.lower() or "time" in k.lower() or "start" in k.lower():
                print(f"- {k}: {data[k]}")

    # Check AAPL (Stock) - often has more fundamental data
    print("\n--- NASDAQ:AAPL ---")
    res = ov.get_symbol_overview("NASDAQ:AAPL")
    if res.get("status") == "success":
        data = res.get("data", {})
        for k in data.keys():
            if "date" in k.lower() or "time" in k.lower() or "start" in k.lower():
                print(f"- {k}: {data[k]}")


if __name__ == "__main__":
    check_fields()
