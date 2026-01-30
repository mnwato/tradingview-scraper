from typing import Optional

import pandas as pd
import pandas_ta_classic as ta


class TechnicalRatings:
    """
    Utility class to reconstruct TradingView technical ratings from OHLCV data.
    Implements the logic for Recommend.MA, Recommend.Other, and Recommend.All.
    """

    @staticmethod
    def calculate_recommend_ma(df: pd.DataFrame) -> float:
        """
        Reconstructs the 'Recommend.MA' rating.
        Components: SMA (10-200), EMA (10-200), VWMA(20), HullMA(9), Ichimoku.
        """
        if df.empty:
            return 0.0

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Ensure volume exists for VWMA
        volume = df["volume"] if "volume" in df.columns else None

        votes = []

        # 1. SMAs & EMAs (Lengths 10, 20, 30, 50, 100, 200)
        lengths = [10, 20, 30, 50, 100, 200]

        for length in lengths:
            # SMA
            sma = ta.sma(close, length=length)
            if sma is not None:
                val = sma.iloc[-1]
                curr = close.iloc[-1]
                votes.append(1 if curr > val else -1)

            # EMA
            ema = ta.ema(close, length=length)
            if ema is not None:
                val = ema.iloc[-1]
                curr = close.iloc[-1]
                votes.append(1 if curr > val else -1)

        # 2. Hull MA (9)
        hma = ta.hma(close, length=9)
        if hma is not None:
            val = hma.iloc[-1]
            curr = close.iloc[-1]
            votes.append(1 if curr > val else -1)

        # 3. VWMA (20)
        if volume is not None:
            vwma = ta.vwma(close, volume, length=20)
            if vwma is not None:
                val = vwma.iloc[-1]
                curr = close.iloc[-1]
                votes.append(1 if curr > val else -1)

        # 4. Ichimoku (9, 26, 52) - Price vs Cloud
        # Note: In pandas_ta, spans are aligned with current index.
        # TV logic compares Price(t) with Cloud projected to (t).
        # Cloud(t) is derived from SpanA/B calculated at (t-26).
        ichimoku_df, _ = ta.ichimoku(high, low, close, tenkan=9, kijun=26, senkou=52)
        if ichimoku_df is not None and len(ichimoku_df) > 26:
            # Shift back 26 periods to get the span values that project to 'now'
            # ISA_9 and ISB_26 at index -27 project to index -1 (current candle)
            # Standard displacement is 26.
            span_a = ichimoku_df["ISA_9"].iloc[-27]
            span_b = ichimoku_df["ISB_26"].iloc[-27]

            if pd.notna(span_a) and pd.notna(span_b):
                mn = min(span_a, span_b)
                mx = max(span_a, span_b)
                curr = close.iloc[-1]

                if curr > mx:
                    votes.append(1)
                elif curr < mn:
                    votes.append(-1)
                else:
                    votes.append(0)  # Neutral
            else:
                votes.append(0)
        else:
            votes.append(0)

        # Aggregate
        if not votes:
            return 0.0

        buy_votes = votes.count(1)
        sell_votes = votes.count(-1)
        return (buy_votes - sell_votes) / len(votes)

    @staticmethod
    def calculate_recommend_other(df: pd.DataFrame) -> float:
        """
        Reconstructs the 'Recommend.Other' (Oscillators) rating.
        Components: RSI, Stoch, CCI, ADX, AO, Mom, MACD, StochRSI, WillR, BBP, UO.
        """
        if df.empty:
            return 0.0

        close = df["close"]
        high = df["high"]
        low = df["low"]

        votes = []

        # 1. RSI (14)
        rsi = ta.rsi(close, length=14)
        if rsi is not None:
            val = rsi.iloc[-1]
            if val < 30:
                votes.append(1)
            elif val > 70:
                votes.append(-1)
            else:
                votes.append(0)

        # 2. Stochastic (14, 3, 3)
        stoch = ta.stoch(high, low, close, k=14, d=3, smooth_k=3)
        if stoch is not None:
            k = stoch["STOCHk_14_3_3"].iloc[-1]
            d = stoch["STOCHd_14_3_3"].iloc[-1]
            if k < 20 and k > d:
                votes.append(1)
            elif k > 80 and k < d:
                votes.append(-1)
            else:
                votes.append(0)

        # 3. CCI (20)
        cci = ta.cci(high, low, close, length=20)
        if cci is not None:
            val = cci.iloc[-1]
            if val < -100:
                votes.append(1)
            elif val > 100:
                votes.append(-1)
            else:
                votes.append(0)

        # 4. ADX (14, 14)
        adx = ta.adx(high, low, close, length=14)
        if adx is not None:
            adx_val = adx["ADX_14"].iloc[-1]
            dmp = adx["DMP_14"].iloc[-1]
            dmn = adx["DMN_14"].iloc[-1]
            if adx_val > 20:
                if dmp > dmn:
                    votes.append(1)
                elif dmn > dmp:
                    votes.append(-1)
                else:
                    votes.append(0)
            else:
                votes.append(0)

        # 5. AO (Awesome Oscillator)
        ao = ta.ao(high, low)
        if ao is not None:
            val = ao.iloc[-1]
            prev = ao.iloc[-2]
            if val > 0 and val > prev:
                votes.append(1)
            elif val < 0 and val < prev:
                votes.append(-1)
            else:
                votes.append(0)

        # 6. Momentum (10)
        mom = ta.mom(close, length=10)
        if mom is not None:
            val = mom.iloc[-1]
            votes.append(1 if val > 0 else -1)

        # 7. MACD (12, 26, 9)
        macd = ta.macd(close, fast=12, slow=26, signal=9)
        if macd is not None:
            hist = macd["MACDh_12_26_9"].iloc[-1]
            votes.append(1 if hist > 0 else -1)

        # 8. Stochastic RSI (3, 3, 14, 14)
        stochrsi = ta.stochrsi(close, length=14, rsi_length=14, k=3, d=3)
        if stochrsi is not None:
            k = stochrsi["STOCHRSIk_14_14_3_3"].iloc[-1]
            if k < 20:
                votes.append(1)
            elif k > 80:
                votes.append(-1)
            else:
                votes.append(0)

        # 9. Williams %R (14)
        willr = ta.willr(high, low, close, length=14)
        if willr is not None:
            val = willr.iloc[-1]
            if val < -80:
                votes.append(1)
            elif val > -20:
                votes.append(-1)
            else:
                votes.append(0)

        # 10. Bull Bear Power (13)
        ema13 = ta.ema(close, length=13)
        if ema13 is not None:
            bull = high.iloc[-1] - ema13.iloc[-1]
            bear = low.iloc[-1] - ema13.iloc[-1]
            val = bull + bear

            prev_bull = high.iloc[-2] - ema13.iloc[-2]
            prev_bear = low.iloc[-2] - ema13.iloc[-2]
            prev_val = prev_bull + prev_bear

            if val > 0 and val > prev_val:
                votes.append(1)
            elif val < 0 and val < prev_val:
                votes.append(-1)
            else:
                votes.append(0)

        # 11. Ultimate Oscillator (7, 14, 28)
        uo = ta.uo(high, low, close, fast=7, medium=14, slow=28)
        if uo is not None:
            val = uo.iloc[-1]
            if val < 30:
                votes.append(1)
            elif val > 70:
                votes.append(-1)
            else:
                votes.append(0)

        # Aggregate
        if not votes:
            return 0.0

        buy_votes = votes.count(1)
        sell_votes = votes.count(-1)
        return (buy_votes - sell_votes) / len(votes)

    @staticmethod
    def calculate_recommend_all(df: pd.DataFrame, ma_score: Optional[float] = None, osc_score: Optional[float] = None) -> float:
        """
        Reconstructs the 'Recommend.All' composite rating.
        Formula: 0.574 * MA + 0.3914 * Other (Derived empirically).
        """
        if ma_score is None:
            ma_score = TechnicalRatings.calculate_recommend_ma(df)
        if osc_score is None:
            osc_score = TechnicalRatings.calculate_recommend_other(df)

        return (0.574 * ma_score) + (0.3914 * osc_score)
