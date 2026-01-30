import logging

from tradingview_scraper.futures_universe_selector import FuturesUniverseSelector

# Setup logging
logging.basicConfig(level=logging.INFO)


def run_scan(config_path, title):
    print(f"\n--- Running {title} Scan ---")
    print(f"Loading config from {config_path}")

    selector = FuturesUniverseSelector(config_path)
    result = selector.run()

    candidates = result.get("data", [])
    print(f"Total candidates found: {len(candidates)}")

    if candidates:
        print(f"\n{title} Candidates:")
        print(f"| {'Symbol':<20} | {'Rec':<5} | {'RSI':<6} | {'Stoch.K':<7} | {'Perf.W':<8} | {'Change%':<8} |")
        print(f"|{'-' * 22}|{'-' * 7}|{'-' * 8}|{'-' * 9}|{'-' * 10}|{'-' * 10}|")

        for row in candidates[:20]:
            sym = row.get("symbol", "").replace("BINANCE:", "").replace("NASDAQ:", "").replace("NYSE:", "")
            rec = row.get("Recommend.All")
            rsi = row.get("RSI")
            stoch = row.get("Stoch.K")
            pw = row.get("Perf.W")
            chg = row.get("change")

            # Format nicely
            rec_str = f"{rec:.2f}" if rec is not None else "-"
            rsi_str = f"{rsi:.1f}" if rsi is not None else "-"
            stoch_str = f"{stoch:.1f}" if stoch is not None else "-"
            pw_str = f"{pw:.2f}%" if pw is not None else "-"
            chg_str = f"{chg:.2f}%" if chg is not None else "-"

            print(f"| {sym:<20} | {rec_str:<5} | {rsi_str:<6} | {stoch_str:<7} | {pw_str:<8} | {chg_str:<8} |")
    else:
        print("No candidates found.")


def main():
    # 1. Crypto Mean Reversion
    run_scan("configs/crypto_cex_ts_mean_reversion_long.yaml", "Crypto TS Mean Reversion (Long)")

    # 2. US Stocks Mean Reversion
    run_scan("configs/us_stocks_mean_reversion.yaml", "US Stocks Mean Reversion (Long)")


if __name__ == "__main__":
    main()
