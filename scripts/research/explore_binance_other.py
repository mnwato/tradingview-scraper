import logging

import pandas as pd

from tradingview_scraper.futures_universe_selector import (
    FuturesUniverseSelector,
    SelectorConfig,
    TrendConfig,
    TrendRuleConfig,
    VolumeConfig,
)

logging.basicConfig(level=logging.INFO)


def explore_binance_spot_other():
    logging.info("Fetching raw data for BINANCE...")
    config = SelectorConfig(
        markets=["crypto"],
        exchanges=["BINANCE"],
        limit=500,
        sort_by="Value.Traded",
        sort_order="desc",
        market_cap_rank_limit=None,
        market_cap_floor=0,
        volume=VolumeConfig(value_traded_min=0, min=0),
        trend=TrendConfig(recommendation=TrendRuleConfig(enabled=False), adx=TrendRuleConfig(enabled=False), momentum=TrendRuleConfig(enabled=False)),
        dedupe_by_symbol=False,
    )

    selector = FuturesUniverseSelector(config)
    selector.config.columns = ["name", "close", "volume", "Value.Traded"]

    data = selector.run().get("data", [])

    binance_other_spot = []
    for r in data:
        sym = r["symbol"]
        # Basic product type check
        is_perp = sym.upper().endswith(".P")
        if is_perp:
            continue

        base, quote = FuturesUniverseSelector._extract_base_quote(sym)
        if not quote or quote == "":  # This is what ends up as OTHER
            binance_other_spot.append({"symbol": sym, "value_traded": float(r.get("Value.Traded") or 0)})

    df = pd.DataFrame(binance_other_spot)
    print(f"\n{'=' * 20} Binance Spot 'OTHER' Quote Breakdown {'=' * 20}")
    print(f"Total Count: {len(df)}")
    if not df.empty:
        print(df.sort_values("value_traded", ascending=False).to_string(index=False))


if __name__ == "__main__":
    explore_binance_spot_other()
