import argparse
from pathlib import Path

import pandas as pd
import pandas_ta_classic as ta


def reconstruct_osc_rating(symbol: str = "BINANCE:BTCUSDT"):
    # 1. Load Data
    # -------------------------------------------------------------------------
    # OHLCV
    # Sanitize symbol for filename (e.g. BINANCE:BTCUSDT -> BINANCE_BTCUSDT)
    safe_symbol = symbol.replace(":", "_")
    ohlcv_path = Path(f"data/lakehouse/{safe_symbol}_1d.parquet")
    if not ohlcv_path.exists():
        print(f"OHLCV not found: {ohlcv_path}")
        return

    df = pd.read_parquet(ohlcv_path)
    df.columns = [c.lower() for c in df.columns]

    # Feature Snapshot (Ground Truth)
    feat_base = Path("data/lakehouse/features/tv_technicals_1d")
    date_dirs = sorted(list(feat_base.glob("date=*")))
    if not date_dirs:
        print("No feature snapshots found.")
        return

    # Iterate partitions to find symbol
    latest_feat_path = None
    gt_df = pd.DataFrame()

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

    # Filter for Symbol
    row = gt_df[gt_df["symbol"] == symbol].iloc[0]
    actual_score = row["recommend_other_1d"]
    print(f"Actual TradingView Oscillator Score (Today) for {symbol}: {actual_score}")

    # 2. Calculate Indicators
    # -------------------------------------------------------------------------
    votes = []
    close = df["close"]
    high = df["high"]
    low = df["low"]

    print("\n--- Component Breakdown ---")

    # 1. RSI (14)
    # Buy < 30, Sell > 70
    rsi = ta.rsi(close, length=14)
    if rsi is not None:
        val = rsi.iloc[-1]
        vote = 0
        if val < 30:
            vote = 1
        elif val > 70:
            vote = -1
        votes.append(vote)
        print(f"RSI 14: {val:.2f} -> {vote}")

    # 2. Stochastic (14, 3, 3)
    # Buy < 20, Sell > 80 (using K)
    stoch = ta.stoch(high, low, close, k=14, d=3, smooth_k=3)
    if stoch is not None:
        # Columns: STOCHk_14_3_3, STOCHd_14_3_3
        k = stoch["STOCHk_14_3_3"].iloc[-1]
        d = stoch["STOCHd_14_3_3"].iloc[-1]
        vote = 0

        # Refined Logic: Overbought/Oversold requires K/D confirmation?
        # Standard: K > 80 is Sell.
        # But if K > D (still rising), maybe Neutral?
        # Let's try: Sell if K > 80 AND K < D (Cross Down). Buy if K < 20 AND K > D (Cross Up).

        if k < 20 and k > d:
            vote = 1
        elif k > 80 and k < d:
            vote = -1

        # If just K > 80 but K > D -> Neutral (Strong Trend)

        votes.append(vote)
        print(f"Stoch K: {k:.2f} (D: {d:.2f}) -> {vote}")

    # 3. CCI (20)
    # Buy < -100, Sell > 100
    cci = ta.cci(high, low, close, length=20)
    if cci is not None:
        val = cci.iloc[-1]
        vote = 0
        if val < -100:
            vote = 1
        elif val > 100:
            vote = -1
        votes.append(vote)
        print(f"CCI 20: {val:.2f} -> {vote}")

    # 4. ADX (14, 14)
    # Buy if ADX > 20 and DI+ > DI-. Sell if ADX > 20 and DI- > DI+.
    adx = ta.adx(high, low, close, length=14)
    if adx is not None:
        # Columns: ADX_14, DMP_14, DMN_14 (Plus, Minus)
        adx_val = adx["ADX_14"].iloc[-1]
        dmp = adx["DMP_14"].iloc[-1]
        dmn = adx["DMN_14"].iloc[-1]
        vote = 0
        # TradingView logic check:
        # Sometimes ADX isn't directional itself, but filter?
        # But for Rating, it usually contributes.
        if adx_val > 20:
            if dmp > dmn:
                vote = 1
            elif dmn > dmp:
                vote = -1
        votes.append(vote)
        print(f"ADX 14: {adx_val:.2f} (D+ {dmp:.2f}, D- {dmn:.2f}) -> {vote}")

    # 5. AO (Awesome Oscillator)
    # Logic: Buy if Rising (> 0 or just Rising?), Sell if Falling.
    # Refined: AO > 0 and Rising = Buy. AO < 0 and Falling = Sell.
    ao = ta.ao(high, low)
    if ao is not None:
        val = ao.iloc[-1]
        prev = ao.iloc[-2]

        vote = 0
        # Logic: Zero Cross or Saucer?
        # Standard TV rating logic is often:
        # Buy: AO > Prev (Rising) AND (AO > 0 OR AO Crosses 0)
        # Sell: AO < Prev (Falling) AND (AO < 0 OR AO Crosses 0)
        # Let's try: Vote based on Trend relative to Zero?
        # Current working hypothesis: Buy if > 0 and Rising. Sell if < 0 and Falling.

        if val > 0 and val > prev:
            vote = 1
        elif val < 0 and val < prev:
            vote = -1

        votes.append(vote)
        print(f"AO: {val:.2f} (Prev {prev:.2f}) -> {vote}")

    # 6. Momentum (10)
    # Buy > 0, Sell < 0.
    mom = ta.mom(close, length=10)
    if mom is not None:
        val = mom.iloc[-1]
        vote = 1 if val > 0 else -1
        votes.append(vote)
        print(f"Mom 10: {val:.2f} -> {vote}")

    # 7. MACD (12, 26, 9)
    # Buy > Signal, Sell < Signal
    macd = ta.macd(close, fast=12, slow=26, signal=9)
    if macd is not None:
        hist = macd["MACDh_12_26_9"].iloc[-1]
        vote = 1 if hist > 0 else -1
        votes.append(vote)
        print(f"MACD Hist: {hist:.2f} -> {vote}")

    # 8. Stochastic RSI (3, 3, 14, 14)
    # Buy < 20, Sell > 80
    stochrsi = ta.stochrsi(close, length=14, rsi_length=14, k=3, d=3)
    if stochrsi is not None:
        k = stochrsi["STOCHRSIk_14_14_3_3"].iloc[-1]
        vote = 0
        if k < 20:
            vote = 1
        elif k > 80:
            vote = -1
        votes.append(vote)
        print(f"StochRSI K: {k:.2f} -> {vote}")

    # 9. Williams %R (14)
    # Buy < -80, Sell > -20
    willr = ta.willr(high, low, close, length=14)
    if willr is not None:
        val = willr.iloc[-1]
        vote = 0
        if val < -80:
            vote = 1
        elif val > -20:
            vote = -1
        votes.append(vote)
        print(f"WillR: {val:.2f} -> {vote}")

    # 10. Bulls and Bears Power (13)
    # Logic: Vote = 1 if (Bull + Bear) > 0 AND Rising.
    ema13 = ta.ema(close, length=13)
    if ema13 is not None:
        bull = high.iloc[-1] - ema13.iloc[-1]
        bear = low.iloc[-1] - ema13.iloc[-1]

        prev_bull = high.iloc[-2] - ema13.iloc[-2]
        prev_bear = low.iloc[-2] - ema13.iloc[-2]

        val = bull + bear
        prev_val = prev_bull + prev_bear

        vote = 0
        if val > 0 and val > prev_val:
            vote = 1
        elif val < 0 and val < prev_val:
            vote = -1

        votes.append(vote)
        print(f"BBP: {val:.2f} (Prev {prev_val:.2f}) -> {vote}")

    # 11. Ultimate Oscillator (7, 14, 28)
    # Buy < 30, Sell > 70
    uo = ta.uo(high, low, close, fast=7, medium=14, slow=28)
    if uo is not None:
        val = uo.iloc[-1]
        vote = 0
        if val < 30:
            vote = 1
        elif val > 70:
            vote = -1
        votes.append(vote)
        print(f"UO: {val:.2f} -> {vote}")

    # 3. Aggregate
    # -------------------------------------------------------------------------
    total_votes = len(votes)
    buy_votes = votes.count(1)
    sell_votes = votes.count(-1)

    if total_votes == 0:
        print("No indicators calculated.")
        return

    raw_score = (buy_votes - sell_votes) / total_votes

    print("\n--- Result ---")
    print(f"Total Components: {total_votes}")
    print(f"Buys: {buy_votes}")
    print(f"Sells: {sell_votes}")
    print(f"Calculated Score: {raw_score:.4f}")
    print(f"Actual Score:     {actual_score:.4f}")

    diff = abs(raw_score - actual_score)
    print(f"Difference: {diff:.4f}")

    # 2 decimal places tolerance (approx 1/11 ~ 0.09)
    if diff < 0.1:
        print("✅ SUCCESS: Reconstruction matches within tolerance.")
    else:
        print("❌ FAILURE: Significant deviation.")

    # 4. Verify Library Implementation
    # -------------------------------------------------------------------------
    from tradingview_scraper.utils.technicals import TechnicalRatings

    lib_score = TechnicalRatings.calculate_recommend_other(df)
    print(f"\nLibrary Score: {lib_score:.4f}")

    if abs(lib_score - raw_score) < 0.0001:
        print("✅ LIBRARY VERIFIED: Utility class matches research logic.")
    else:
        print(f"❌ LIBRARY MISMATCH: {lib_score:.4f} vs {raw_score:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BINANCE:BTCUSDT", help="Symbol to check")
    args = parser.parse_args()

    reconstruct_osc_rating(args.symbol)
