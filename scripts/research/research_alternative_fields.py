from tradingview_scraper.symbols.screener import Screener


def check():
    screener = Screener()
    # Let's try to request "all" known fields or guess names
    # Common TV fields: "listed_date", "start_date", "genesis_date", "ipo_date"
    # Also "provider_id", "source_id"

    candidates = ["listed_date", "start_date", "genesis_date", "ipo_date", "launch_date", "creation_date", "first_trade_date"]

    print(f"Checking for candidates: {candidates}")

    filters = [{"left": "exchange", "operation": "equal", "right": "BINANCE"}, {"left": "name", "operation": "equal", "right": "BTCUSDT"}]

    # We have to be careful, if we request an unknown column, TV might return error
    # Let's try one by one?

    for field in candidates:
        try:
            res = screener.screen(market="crypto", filters=filters, columns=["name", field], limit=1)
            if res["status"] == "success":
                print(f"Field '{field}' exists: {res['data'][0]}")
            else:
                # print(f"Field '{field}' failed: {res.get('error')}")
                pass
        except Exception as e:
            pass


if __name__ == "__main__":
    check()
