import json

import pandas as pd

from tradingview_scraper.settings import get_settings
from tradingview_scraper.symbols.screener import Screener


def scan_arbitrage():
    settings = get_settings()
    # 1. Load the multi-quote mapping
    mapping_file = settings.export_dir / "multi_quote_mapping.json"
    if not mapping_file.exists():
        print(f"[ERROR] Mapping file {mapping_file} not found. Run audit_multi_quote_pairs.py first.")
        return

    with open(mapping_file, "r") as f:
        mapping = json.load(f)

    # 2. Collect all symbols to fetch
    all_symbols = []
    for primary, alts in mapping.items():
        all_symbols.append(primary)
        all_symbols.extend(alts)

    all_names = list(set([s.split(":")[1] for s in all_symbols]))
    print(f"[INFO] Fetching snapshot data for {len(all_names)} symbol names via Screener...")

    # 3. Fetch snapshots via Screener
    screener = Screener()

    columns = ["name", "bid", "ask", "close", "volume"]

    # Filter by name, but we will post-process for EXCHANGE consistency
    results = screener.screen(
        market="crypto",
        filters=[{"left": "name", "operation": "in_range", "right": all_names}],
        columns=columns,
        limit=1000,  # Increase limit to capture all exchanges
    )

    if results["status"] != "success":
        print(f"[ERROR] Screener failed: {results.get('error')}")
        return

    # Post-process: Filter for Binance only and create snapshot map
    snapshots = {}
    for item in results["data"]:
        symbol = item["symbol"]
        if "BINANCE" in symbol:
            snapshots[symbol] = item

    print(f"[INFO] Captured {len(snapshots)} Binance symbols.")

    # 4. Calculate spreads
    arbitrage_ops = []

    for primary, alts in mapping.items():
        if primary not in snapshots:
            continue

        p_data = snapshots[primary]
        p_bid = p_data.get("bid") or p_data.get("close")
        p_ask = p_data.get("ask") or p_data.get("close")

        if p_bid is None or p_ask is None:
            continue

        for alt in alts:
            if alt not in snapshots:
                continue
            a_data = snapshots[alt]
            a_bid = a_data.get("bid") or a_data.get("close")
            a_ask = a_data.get("ask") or a_data.get("close")

            if a_bid is None or a_ask is None:
                continue

            # Spread A vs P
            spread_buy_p_sell_a = (a_bid / p_ask - 1) * 100
            spread_buy_a_sell_p = (p_bid / a_ask - 1) * 100

            max_spread = max(spread_buy_p_sell_a, spread_buy_a_sell_p)
            direction = "Buy P / Sell A" if spread_buy_p_sell_a > spread_buy_a_sell_p else "Buy A / Sell P"

            arbitrage_ops.append(
                {
                    "Type": "PERP" if ".P" in primary else "SPOT",
                    "Primary": primary,
                    "Alt": alt,
                    "P_Price": (p_bid + p_ask) / 2,
                    "A_Price": (a_bid + a_ask) / 2,
                    "Max Spread %": max_spread,
                    "Direction": direction,
                }
            )

    if not arbitrage_ops:
        print("[INFO] No comparable pair snapshots found in screener results.")
        return

    df = pd.DataFrame(arbitrage_ops)
    df = df.sort_values("Max Spread %", ascending=False)

    print("\n" + "=" * 140)
    print("REAL-TIME MULTI-QUOTE ARBITRAGE ANALYSIS (via Screener Snapshot)")
    print("=" * 140)
    print(df[["Type", "Primary", "Alt", "Max Spread %", "Direction"]].to_string(index=False))

    high_spread = df[df["Max Spread %"] > 0.05]
    if not high_spread.empty:
        print("\n>>> Potential Arbitrage Discrepancies (> 0.05% before fees) <<<")
        print(high_spread[["Type", "Primary", "Alt", "Max Spread %", "Direction"]].to_string(index=False))
    else:
        print("\n[INFO] No significant arbitrage opportunities (> 0.05%) detected.")


if __name__ == "__main__":
    scan_arbitrage()
