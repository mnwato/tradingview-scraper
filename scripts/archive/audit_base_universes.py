import logging
import os
import re

import pandas as pd

from tradingview_scraper.futures_universe_selector import FuturesUniverseSelector, load_config

logging.basicConfig(level=logging.INFO)

EXCHANGES = ["BINANCE", "OKX", "BYBIT", "BITGET"]


def get_product_type(symbol: str) -> str:
    if symbol.upper().endswith(".P"):
        return "PERP"
    core = symbol.split(":", 1)[-1].upper().replace(".P", "")
    patterns = [r"[0-9]{1,2}[A-Z][0-9]{2,4}$", r"[A-Z]{1,3}[0-9]{2,4}$"]
    if any(re.search(pat, core) for pat in patterns):
        return "DATED"
    return "SPOT"


def audit_exchange_type(exchange: str, suffix: str):
    config_file = f"configs/crypto_cex_base_top50_{exchange.lower()}{suffix}.yaml"
    if not os.path.exists(config_file):
        return

    print(f"\n{'#' * 80}")
    print(f"### AUDIT: {exchange} {'PERP' if suffix else 'SPOT'}")
    print(f"{'#' * 80}")

    config = load_config(config_file)
    # We want to see EVERYTHING that passed initial filters before dedupe
    config.limit = 500
    config.base_universe_limit = 500
    config.dedupe_by_symbol = False

    selector = FuturesUniverseSelector(config)
    data_resp = selector.run()
    raw_data = data_resp.get("data", [])

    if not raw_data:
        print(f"No data found for {config_file}")
        return

    df = pd.DataFrame(raw_data)
    df["base"] = df["symbol"].apply(selector._base_symbol)
    df["type"] = df["symbol"].apply(get_product_type)

    # Track what the selector WOULD pick vs what it would discard
    best_by_base = {}
    discarded = []

    # Simulating _aggregate_by_base but with more tracking
    aggregated = selector._aggregate_by_base(raw_data)
    selected_symbols = {r["symbol"] for r in aggregated}

    for _, row in df.iterrows():
        if row["symbol"] in selected_symbols:
            best_by_base[row["base"]] = row
        else:
            discarded.append(row)

    df_dis = pd.DataFrame(discarded)

    print("\n--- 1. Summary ---")
    print(f"Total Tradeable Candidates (Raw): {len(df)}")
    print(f"Unique Base Assets Selected: {len(aggregated)}")
    print(f"Duplicates Discarded: {len(discarded)}")

    print("\n--- 2. Duplicate Treatment Examples (Top 5 Bases with Dupes) ---")
    base_counts = df["base"].value_counts()
    multi_bases = base_counts[base_counts > 1].index[:5]

    for base in multi_bases:
        base_df = df[df["base"] == base].sort_values("Value.Traded", ascending=False)
        print(f"\nBase Asset: {base}")
        for _, r in base_df.iterrows():
            status = "[WINNER]" if r["symbol"] in selected_symbols else "[DISCARDED]"
            print(f"  {status} {r['symbol']} | VT: ${r['Value.Traded']:,.0f} | Type: {r['type']}")

    print("\n--- 3. Top 10 Winners by Liquidity ---")
    df_winners = pd.DataFrame(aggregated).sort_values("Value.Traded", ascending=False).head(10)
    print(df_winners[["symbol", "Value.Traded", "market_cap_external"]].to_string(index=False))

    print("\n--- 4. Bottom 5 Winners (Liquidity Floor Check) ---")
    df_tail = pd.DataFrame(aggregated).sort_values("Value.Traded", ascending=False).tail(5)
    print(df_tail[["symbol", "Value.Traded"]].to_string(index=False))


def run_audit():
    for ex in EXCHANGES:
        for suffix in ["", "_perp"]:
            audit_exchange_type(ex, suffix)


if __name__ == "__main__":
    run_audit()
