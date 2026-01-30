from tradingview_scraper.symbols.overview import Overview


def check_fields():
    ov = Overview()
    # Fetch all fields
    res = ov.get_symbol_overview("BINANCE:BTCUSDT")
    if res.get("status") == "success":
        data = res.get("data", {})
        print("Available fields in Overview:")
        for k in sorted(data.keys()):
            print(f"- {k}: {data[k]}")
    else:
        print("Error:", res)


if __name__ == "__main__":
    check_fields()
