from pathlib import Path

import pandas as pd
import pandas_ta_classic as ta


def reconstruct_ma_rating():
    # 1. Load Data
    # -------------------------------------------------------------------------
    # OHLCV
    ohlcv_path = Path("data/lakehouse/BINANCE_BTCUSDT_1d.parquet")
    if not ohlcv_path.exists():
        print(f"OHLCV not found: {ohlcv_path}")
        return

    df = pd.read_parquet(ohlcv_path)
    # Ensure standard columns (lower case)
    df.columns = [c.lower() for c in df.columns]

    # Feature Snapshot (Ground Truth)
    # Find the latest partition
    feat_base = Path("data/lakehouse/features/tv_technicals_1d")
    date_dirs = sorted(list(feat_base.glob("date=*")))
    if not date_dirs:
        print("No feature snapshots found.")
        return

    # Iterate partitions to find symbol
    latest_feat_path = None
    gt_df = pd.DataFrame()
    symbol = "BINANCE:BTCUSDT"

    # Search backwards for the symbol in recent partitions
    for d in reversed(date_dirs):
        for f in d.glob("*.parquet"):
            temp = pd.read_parquet(f)
            if symbol in temp["symbol"].values:
                gt_df = temp
                latest_feat_path = f
                break
        if not gt_df.empty:
            break

    if gt_df.empty:
        print(f"{symbol} not found in any feature snapshot.")
        return

    print(f"Loading Ground Truth from: {latest_feat_path}")

    # Filter for BTC
    btc_gt = gt_df[gt_df["symbol"] == symbol]
    actual_score = btc_gt.iloc[0]["recommend_ma_1d"]
    print(f"Actual TradingView Score (Today): {actual_score}")

    # 2. Calculate Indicators
    # -------------------------------------------------------------------------
    # We need the LAST row of the calculation to compare with the snapshot
    # Assuming snapshot was taken "recently" and OHLCV is up to date.

    # Simple Moving Averages (10, 20, 30, 50, 100, 200)
    smas = [10, 20, 30, 50, 100, 200]
    votes = []

    close = df["close"]

    print("\n--- Component Breakdown ---")

    # SMA
    for length in smas:
        ma = ta.sma(close, length=length)
        if ma is None:
            continue
        val = ma.iloc[-1]
        curr = close.iloc[-1]
        vote = 1 if curr > val else -1
        votes.append(vote)
        print(f"SMA {length}: {curr:.2f} vs {val:.2f} -> {vote}")

    # EMA
    emas = [10, 20, 30, 50, 100, 200]
    for length in emas:
        ma = ta.ema(close, length=length)
        if ma is None:
            continue
        val = ma.iloc[-1]
        curr = close.iloc[-1]
        vote = 1 if curr > val else -1
        votes.append(vote)
        print(f"EMA {length}: {curr:.2f} vs {val:.2f} -> {vote}")

    # Hull MA (9)
    hma = ta.hma(close, length=9)
    if hma is not None:
        val = hma.iloc[-1]
        curr = close.iloc[-1]
        vote = 1 if curr > val else -1
        votes.append(vote)
        print(f"HMA 9: {curr:.2f} vs {val:.2f} -> {vote}")

    # VWMA (20)
    # Requires volume
    if "volume" in df.columns:
        vwma = ta.vwma(close, df["volume"], length=20)
        if vwma is not None:
            val = vwma.iloc[-1]
            curr = close.iloc[-1]
            vote = 1 if curr > val else -1
            votes.append(vote)
            print(f"VWMA 20: {curr:.2f} vs {val:.2f} -> {vote}")
    else:
        print("VWMA 20: Skipped (No Volume)")

    # Ichimoku (9, 26, 52)
    # TradingView logic for Ichimoku Rating:
    # Likely Price vs Cloud (Kumo)
    # Cloud is formed by Span A and Span B, shifted forward by 26.
    # So Current Cloud value corresponds to values calculated 26 periods ago.

    ichimoku_df, _ = ta.ichimoku(df["high"], df["low"], df["close"], tenkan=9, kijun=26, senkou=52)

    if ichimoku_df is not None:
        curr = close.iloc[-1]

        # We need the Span A and B from 26 periods ago
        # Check if index is large enough
        if len(ichimoku_df) > 26:
            # ISA and ISB at index -26 (relative to end if we consider alignment)
            # pandas_ta returns arrays aligned with input index.
            # Span A/B are traditionally plotted 26 bars ahead.
            # But the values in the dataframe at index T are usually the values calculated at T.
            # To get the Cloud value for "Today" (T), we need the Span A/B that were projected to Today.
            # Span A/B calculated at T-26 are projected to T.

            span_a = ichimoku_df["ISA_9"].iloc[-27]
            span_b = ichimoku_df["ISB_26"].iloc[-27]

            print(f"Ichimoku Cloud (26 ago): Span A {span_a:.2f}, Span B {span_b:.2f}")
            print(f"Current Price: {curr:.2f}")

            if span_a is not None and span_b is not None:
                mn = min(span_a, span_b)
                mx = max(span_a, span_b)

                if curr > mx:
                    vote = 1
                elif curr < mn:
                    vote = -1
                else:
                    vote = 0  # Neutral (Inside Cloud)
            else:
                vote = 0
        else:
            vote = 0

        votes.append(vote)
        print(f"Ichimoku (Price vs Cloud): {vote}")

    # 3. Aggregate
    # -------------------------------------------------------------------------
    total_votes = len(votes)
    buy_votes = votes.count(1)
    sell_votes = votes.count(-1)
    neutral_votes = votes.count(0)

    raw_score = (buy_votes - sell_votes) / total_votes if total_votes > 0 else 0

    print("\n--- Result ---")
    print(f"Total Components: {total_votes}")
    print(f"Buys: {buy_votes}")
    print(f"Sells: {sell_votes}")
    print(f"Calculated Score: {raw_score:.4f}")
    print(f"Actual Score:     {actual_score:.4f}")

    diff = abs(raw_score - actual_score)
    print(f"Difference: {diff:.4f}")

    if diff < 0.1:
        print("✅ SUCCESS: Reconstruction matches within tolerance.")
    else:
        print("❌ FAILURE: Significant deviation. Logic refinement needed.")

    # 4. Verify Library Implementation
    # -------------------------------------------------------------------------
    from tradingview_scraper.utils.technicals import TechnicalRatings

    lib_score = TechnicalRatings.calculate_recommend_ma(df)
    print(f"\nLibrary Score: {lib_score:.4f}")

    if abs(lib_score - raw_score) < 0.0001:
        print("✅ LIBRARY VERIFIED: Utility class matches research logic.")
    else:
        print(f"❌ LIBRARY MISMATCH: {lib_score:.4f} vs {raw_score:.4f}")


if __name__ == "__main__":
    reconstruct_ma_rating()
