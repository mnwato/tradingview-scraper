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

    # Logic for dated futures
    core = symbol.split(":", 1)[-1].upper().replace(".P", "")
    patterns = [r"[0-9]{1,2}[A-Z][0-9]{2,4}$", r"[A-Z]{1,3}[0-9]{2,4}$"]
    if any(re.search(pat, core) for pat in patterns):
        return "DATED"

    return "SPOT"


def analyze_config(config_file: str):
    print(f"\n>>> Analyzing Config: {config_file} <<<")

    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found")
        return

    config = load_config(config_file)
    config.limit = 200
    config.base_universe_limit = 200
    config.trend.recommendation.enabled = False
    config.trend.adx.enabled = False
    config.trend.momentum.enabled = False
    config.dedupe_by_symbol = False

    selector = FuturesUniverseSelector(config)

    data_resp = selector.run()
    raw_data = data_resp.get("data", [])
    df = pd.DataFrame(raw_data)

    if df.empty:
        print(f"No data found for {config_file}")
        return

    df["type"] = df["symbol"].apply(get_product_type)

    for ptype in ["PERP", "SPOT"]:
        df_type = df[df["type"] == ptype].copy()
        if df_type.empty:
            continue

        print(f"\n--- {ptype} Markets in this config (Count: {len(df_type)}) ---")

        # Apply Aggregation
        aggregated = selector._aggregate_by_base(df_type.to_dict("records"))
        df_agg = pd.DataFrame(aggregated)

        if not df_agg.empty:
            sort_field = "Value.Traded" if "Value.Traded" in df_agg.columns else "volume"
            df_agg = df_agg.sort_values(sort_field, ascending=False)

            print(f"Unique Bases in {ptype}: {len(df_agg)}")
            print(f"\nTop 5 {ptype} (Aggregated):")
            print(df_agg[["symbol", sort_field]].head(5).to_string(index=False))
            print(f"\nBottom 5 {ptype} (Aggregated):")
            print(df_agg[["symbol", sort_field]].tail(5).to_string(index=False))


def explore_all():
    for ex in EXCHANGES:
        for suffix in ["", "_perp"]:
            cfg_path = f"configs/crypto_cex_base_top50_{ex.lower()}{suffix}.yaml"
            analyze_config(cfg_path)


if __name__ == "__main__":
    explore_all()
