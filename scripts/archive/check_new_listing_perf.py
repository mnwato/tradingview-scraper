from tradingview_scraper.symbols.screener import Screener


def check():
    screener = Screener()
    filters = [
        {"left": "exchange", "operation": "equal", "right": "BINANCE"},
        {"left": "name", "operation": "in_range", "right": ["ACTUSDT", "PNUTUSDT", "THEUSDT"]},  # 'in_range' for list? No, 'equal' one by one or 'in_range' might not work for strings list.
    ]
    # Screener doesn't support 'in' for name easily.
    # Let's search by name match or just get recent listings?
    # Or just query one by one.

    symbols = ["ACTUSDT", "PNUTUSDT"]
    for s in symbols:
        f = [{"left": "exchange", "operation": "equal", "right": "BINANCE"}, {"left": "name", "operation": "equal", "right": s}]
        res = screener.screen(market="crypto", filters=f, columns=["name", "Perf.Y", "Perf.1M"])
        if res["data"]:
            print(f"{s}: {res['data'][0]}")
        else:
            print(f"{s}: No data")


if __name__ == "__main__":
    check()
