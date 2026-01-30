import json
import logging

from tradingview_scraper.futures_universe_selector import FuturesUniverseSelector, SelectorConfig

logging.basicConfig(level=logging.INFO)


def test_filters():
    # Case A: Using volume block
    config_a = SelectorConfig(markets=["crypto"], exchanges=["BINANCE"], volume={"value_traded_min": 20000000}, limit=5)
    selector_a = FuturesUniverseSelector(config_a)
    payload_a = selector_a.build_payloads()[0]
    print("\n--- Payload A (volume block) ---")
    print(json.dumps(payload_a["filters"], indent=2))

    # Case B: Using explicit filters list
    config_b = SelectorConfig(markets=["crypto"], exchanges=["BINANCE"], filters=[{"left": "Value.Traded", "operation": "greater", "right": 20000000}], limit=5)
    selector_b = FuturesUniverseSelector(config_b)
    payload_b = selector_b.build_payloads()[0]
    print("\n--- Payload B (explicit filters) ---")
    print(json.dumps(payload_b["filters"], indent=2))

    # Case C: Both (Redundancy check)
    config_c = SelectorConfig(markets=["crypto"], exchanges=["BINANCE"], volume={"value_traded_min": 20000000}, filters=[{"left": "Value.Traded", "operation": "greater", "right": 20000000}], limit=5)
    selector_c = FuturesUniverseSelector(config_c)
    payload_c = selector_c.build_payloads()[0]
    print("\n--- Payload C (Both) ---")
    print(json.dumps(payload_c["filters"], indent=2))


if __name__ == "__main__":
    test_filters()
