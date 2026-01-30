from tradingview_scraper.symbols.screener import Screener


def test_raw_screen():
    screener = Screener()
    # Simple Binance crypto spot screen
    results = screener.screen(market="crypto", filters=[{"left": "exchange", "operation": "equal", "right": "BINANCE"}], columns=["name", "close", "volume"], limit=10)
    print(results)


if __name__ == "__main__":
    test_raw_screen()
