import logging
import re

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


def get_product_type(symbol: str) -> str:
    if symbol.upper().endswith(".P"):
        return "PERP"

    # Use the same logic as the selector for dated futures
    core = symbol.split(":", 1)[-1].upper().replace(".P", "")
    patterns = [r"[0-9]{1,2}[A-Z][0-9]{2,4}$", r"[A-Z]{1,3}[0-9]{2,4}$"]
    if any(re.search(pat, core) for pat in patterns):
        return "DATED"

    return "SPOT"


def explore_quotes():
    all_data = []

    for exchange in EXCHANGES:
        logging.info(f"Fetching raw data for {exchange}...")
        config = SelectorConfig(
            markets=["crypto"],
            exchanges=[exchange],
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
        selector.config.columns = ["name", "close", "volume", "change", "Value.Traded", "market_cap_calc", "Recommend.All", "ADX", "Volatility.D"]

        data = selector.run().get("data", [])

        for r in data:
            sym = r["symbol"]
            base, quote = FuturesUniverseSelector._extract_base_quote(sym)
            prod_type = get_product_type(sym)

            all_data.append({"exchange": exchange, "product_type": prod_type, "symbol": sym, "base": base, "quote": quote or "OTHER", "value_traded": float(r.get("Value.Traded") or 0)})

    df = pd.DataFrame(all_data)

    # 1. Global Aggregation
    print(f"\n{'=' * 20} GLOBAL Liquidity by Quote & Type {'=' * 20}")
    global_stats = df.groupby(["quote", "product_type"]).agg(total_value=("value_traded", "sum"), count=("symbol", "count")).sort_values("total_value", ascending=False)

    global_stats["pct"] = (global_stats["total_value"] / global_stats["total_value"].sum() * 100).round(2)
    print(global_stats.head(15).to_string())

    # 2. Per Exchange Per Product Type Aggregation
    print(f"\n{'=' * 20} PER EXCHANGE & PRODUCT TYPE Liquidity {'=' * 20}")

    for exchange in EXCHANGES:
        print(f"\n>>> {exchange} <<<")
        ex_df = df[df["exchange"] == exchange]

        # Group by type and quote
        type_quote_stats = (
            ex_df.groupby(["product_type", "quote"]).agg(total_value=("value_traded", "sum"), count=("symbol", "count")).sort_values(["product_type", "total_value"], ascending=[True, False])
        )

        # Format for display
        ex_display = type_quote_stats.copy()
        ex_display["total_value"] = ex_display["total_value"].apply(lambda x: f"${x:,.0f}")
        print(ex_display.to_string())


if __name__ == "__main__":
    explore_quotes()
