import json
import logging

from tradingview_scraper.symbols.overview import Overview


def research_metadata_fields():
    logging.basicConfig(level=logging.INFO)
    ov = Overview()

    symbols = [
        "BINANCE:BTCUSDT",  # Crypto
        "NASDAQ:AAPL",  # Stock (US)
        "LSE:VOD",  # Stock (UK)
        "FX_IDC:EURUSD",  # Forex
        "CME_MINI:ES1!",  # Future
        "ICEEUR:B1!",  # Future (Brent)
    ]

    print("\n" + "=" * 80)
    print("TIMEZONE & SESSION DISCOVERY")
    print("=" * 80)

    catalog = {}

    experimental_fields = ["timezone", "exchange_timezone", "session", "exchange", "country", "type"]

    for symbol in symbols:
        print(f"\n>>> Analyzing {symbol} <<<")
        try:
            # Fetch specific experimental fields
            res = ov.get_symbol_overview(symbol, fields=experimental_fields)
            if res["status"] == "success":
                data = res["data"]
                catalog[symbol] = data

                print(f"  {'[FIELD]':<20} | {'[VALUE]':<50}")
                print("-" * 75)
                for k in experimental_fields:
                    val = data.get(k, "MISSING")
                    print(f"  {k:<20} : {str(val):<50}")

            else:
                print(f"  [FAILED] {res.get('error')}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        except Exception as e:
            print(f"  [ERROR] {e}")

    with open("docs/research/metadata_field_audit.json", "w") as f:
        json.dump(catalog, f, indent=2)

    print("\n[DONE] Full field dump saved to docs/research/metadata_field_audit.json")


if __name__ == "__main__":
    research_metadata_fields()
