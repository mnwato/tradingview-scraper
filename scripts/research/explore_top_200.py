import json
import logging

from tradingview_scraper.futures_universe_selector import (
    FuturesUniverseSelector,
    SelectorConfig,
    TrendConfig,
    TrendRuleConfig,
    VolatilityConfig,
    VolumeConfig,
)

logging.basicConfig(level=logging.INFO)

EXCHANGES = ["BINANCE", "OKX", "BYBIT", "BITGET"]


def explore():
    results = {}

    for exchange in EXCHANGES:
        logging.info(f"Fetching top 200 for {exchange}...")
        config = SelectorConfig(
            markets=["crypto"],
            exchanges=[exchange],
            limit=200,
            sort_by="Value.Traded",
            sort_order="desc",
            # Disable most filters to see raw top assets
            market_cap_rank_limit=None,
            market_cap_floor=0,
            volume=VolumeConfig(value_traded_min=0, min=0, per_exchange={}),
            volatility=VolatilityConfig(min=None, max=None, atr_pct_max=None, fallback_use_atr_pct=False),
            trend=TrendConfig(recommendation=TrendRuleConfig(enabled=False), adx=TrendRuleConfig(enabled=False), momentum=TrendRuleConfig(enabled=False)),
            dedupe_by_symbol=True,  # We want to see unique bases now
        )

        selector = FuturesUniverseSelector(config)
        # We need to manually build columns to include what we want to analyze
        selector.config.columns = ["name", "close", "volume", "change", "Value.Traded", "market_cap_calc", "Recommend.All", "ADX"]

        data = selector.run()
        results[exchange] = data.get("data", [])

    # Simple analysis
    all_symbols = []
    base_counts = {}

    for ex, rows in results.items():
        logging.info(f"{ex}: Found {len(rows)} symbols")
        for r in rows:
            sym = r["symbol"]
            all_symbols.append(sym)
            base, quote = FuturesUniverseSelector._extract_base_quote(sym)
            base_counts[base] = base_counts.get(base, 0) + 1

    # Find bases with multiple representations
    duplicates = {base: count for base, count in base_counts.items() if count > 1}
    logging.info(f"Total Unique Bases: {len(base_counts)}")
    logging.info(f"Bases with multiple representations: {len(duplicates)}")

    # Save for manual inspection
    with open("outputs/top_200_exploration.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print some interesting duplicates
    print("\n--- Top Duplicated Bases ---")
    sorted_dupes = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)
    for base, count in sorted_dupes[:20]:
        print(f"{base}: {count} occurrences")


if __name__ == "__main__":
    explore()
