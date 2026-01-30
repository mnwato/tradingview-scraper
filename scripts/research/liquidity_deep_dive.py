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

EXCHANGES = ["BINANCE", "OKX", "BYBIT", "BITGET"]


def deep_dive():
    all_data = []
    for exchange in EXCHANGES:
        logging.info("Fetching raw data for %s...", exchange)
        config = SelectorConfig(
            markets=["crypto"],
            exchanges=[exchange],
            limit=500,
            sort_by="Value.Traded",
            sort_order="desc",
            market_cap_rank_limit=None,
            market_cap_floor=0,
            volume=VolumeConfig(value_traded_min=1, min=0),
            trend=TrendConfig(recommendation=TrendRuleConfig(enabled=False), adx=TrendRuleConfig(enabled=False), momentum=TrendRuleConfig(enabled=False)),
            dedupe_by_symbol=False,
        )
        selector = FuturesUniverseSelector(config)
        data = selector.run().get("data", [])
        for r in data:
            sym = r["symbol"]
            base, quote = FuturesUniverseSelector._extract_base_quote(sym)
            all_data.append({"exchange": exchange, "symbol": sym, "base": base, "quote": quote or "OTHER", "value_traded": float(r.get("Value.Traded") or 0)})
    df = pd.DataFrame(all_data)
    if df.empty:
        print("No liquidity data found.")
        return
    print(f"\n{'=' * 20} TOP 50 LIQUID PAIRS (Global) {'=' * 20}")
    top_50 = df.sort_values("value_traded", ascending=False).head(50)
    print(top_50[["symbol", "value_traded"]].to_string(index=False))
    print(f"\n{'=' * 20} SIGNIFICANT QUOTES (>0.01% share) {'=' * 20}")
    quote_stats = df.groupby("quote")["value_traded"].sum().sort_values(ascending=False)
    total_val = quote_stats.sum()
    if total_val > 0:
        quote_pct = quote_stats / total_val * 100
        significant = quote_pct[quote_pct > 0.01]
        for q, pct in significant.items():
            print(f"{q}: {pct:.2f}% (${quote_stats[q]:,.0f})")
        print(f"\n{'=' * 20} RECOMMENDATION FOR 'PROPER QUOTES' {'=' * 20}")
        proper_quotes = list(significant.index)
        if "OTHER" in proper_quotes:
            proper_quotes.remove("OTHER")
        print(f"Proposed allowed_spot_quotes: {proper_quotes}")
    else:
        print("No aggregate value found.")


if __name__ == "__main__":
    deep_dive()
