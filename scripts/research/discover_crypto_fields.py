import json

from tradingview_scraper.symbols.screener import Screener


def discover_crypto_fields():
    screener = Screener()
    # Broad set of possible classification fields in TradingView
    possible_fields = ["type", "subtype", "sector", "industry", "category", "tags", "submarket", "exchange", "market", "base_currency", "quote_currency", "asset_class", "description", "name"]

    print(f"Testing {len(possible_fields)} potential fields for crypto screener...")

    found_fields = []
    sample_data = {}

    filters = [{"left": "exchange", "operation": "equal", "right": "BINANCE"}, {"left": "name", "operation": "equal", "right": "BTCUSDT"}]

    for field in possible_fields:
        try:
            res = screener.screen(market="crypto", filters=filters, columns=["name", field], limit=1)
            if res["status"] == "success" and res["data"]:
                found_fields.append(field)
                val = res["data"][0].get(field)
                sample_data[field] = val
                print(f"✅ Found field: '{field}' (Sample: {val})")
        except Exception:
            pass

    print("\n--- Summary of valid crypto fields ---")
    print(json.dumps(sample_data, indent=2))


if __name__ == "__main__":
    discover_crypto_fields()
