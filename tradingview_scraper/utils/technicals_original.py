import numpy as np
import pandas as pd
import pandas_ta_classic as ta
from typing import Optional, List, Dict


class TechnicalRatings:
    """
    Utility class to reconstruct TradingView technical ratings from OHLCV data.
    """

    @staticmethod
    def _safe_vote(cond_buy: pd.Series, cond_sell: pd.Series, index: pd.Index) -> pd.Series:
        """Helper to create a vote series with proper alignment."""
        v = pd.Series(0.0, index=index)
        v.loc[cond_buy.reindex(index, fill_value=False).values] = 1.0
        v.loc[cond_sell.reindex(index, fill_value=False).values] = -1.0
        return v

    @staticmethod
    def calculate_recommend_ma_series(df: pd.DataFrame) -> pd.Series:
        """
        Reconstructs the 'Recommend.MA' rating as a time-series.
        Components: SMA (10-200), EMA (10-200), VWMA(20), HullMA(9), Ichimoku.
        """
        if df.empty:
            return pd.Series(dtype=float)

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"] if "volume" in df.columns else None

        all_votes = []

        # Tuning Experiment 1: Reduce lengths list to match TV more closely if possible
        # Standard: 10, 20, 30, 50, 100, 200
        lengths = [10, 20, 30, 50, 100, 200]

        # Tuning Experiment 2: Weighting? No, standard is equal weight.

        for length in lengths:
            # SMA
            sma = ta.sma(close, length=length)
            if sma is not None:
                all_votes.append(TechnicalRatings._safe_vote(close > sma, close < sma, df.index))
            # EMA
            ema = ta.ema(close, length=length)
            if ema is not None:
                all_votes.append(TechnicalRatings._safe_vote(close > ema, close < ema, df.index))

        # 2. Hull MA (9)
        hma = ta.hma(close, length=9)
        if hma is not None:
            all_votes.append(TechnicalRatings._safe_vote(close > hma, close < hma, df.index))

        # 3. VWMA (20)
        if volume is not None:
            vwma = ta.vwma(close, volume, length=20)
            if vwma is not None:
                all_votes.append(TechnicalRatings._safe_vote(close > vwma, close < vwma, df.index))

        # 4. Ichimoku
        ichimoku_df, _ = ta.ichimoku(high, low, close, tenkan=9, kijun=26, senkou=52)
        if ichimoku_df is not None:
            # Tuning Experiment 4: No Shift is better (Delta ~0.26 vs ~0.5).
            # TV Logic likely compares Current Price vs Current Cloud (calculated from T-26).
            # pandas_ta aligns ISB_26 to T.
            # So span_b[T] IS the value of the span B calculated at T.
            # But the cloud is plotted 26 bars forward.
            # So at time T, the "Cloud" is the value of SpanA/B from T-26.
            # This means we DO need to shift(26) to bring T-26 value to T?
            # Wait, shifting +26 moves values from T to T+26.
            # To get value FROM T-26 TO T, we need shift(26).
            # Let's retry shift(26) but verify indices.

            # Hypothesis: Previous shift(26) failed due to NaNs or alignment.
            # Let's try shift(26) again with fill_value=np.nan
            span_a = ichimoku_df["ISA_9"].shift(26)
            span_b = ichimoku_df["ISB_26"].shift(26)

            mx = np.maximum(span_a, span_b)
            mn = np.minimum(span_a, span_b)

            all_votes.append(TechnicalRatings._safe_vote(close > mx, close < mn, df.index))

        if not all_votes:
            return pd.Series(0.0, index=df.index)

        return pd.concat(all_votes, axis=1).mean(axis=1)

    @staticmethod
    def calculate_recommend_ma(df: pd.DataFrame) -> float:
        series = TechnicalRatings.calculate_recommend_ma_series(df)
        return float(series.iloc[-1]) if not series.empty else 0.0

    @staticmethod
    def calculate_recommend_other_series(df: pd.DataFrame) -> pd.Series:
        if df.empty:
            return pd.Series(dtype=float)

        close = df["close"]
        high = df["high"]
        low = df["low"]

        all_votes = []

        # 1. RSI
        rsi = ta.rsi(close, length=14)
        if rsi is not None:
            rsi = rsi.reindex(df.index)
            vote = pd.Series(0.0, index=df.index)
            vote.loc[rsi.values < 30] = 1.0
            vote.loc[rsi.values > 70] = -1.0
            all_votes.append(vote.where(rsi.notna(), np.nan))

        # 2. Stochastic
        stoch = ta.stoch(high, low, close, k=14, d=3, smooth_k=3)
        if stoch is not None:
            stoch = stoch.reindex(df.index)
            k, d = stoch["STOCHk_14_3_3"], stoch["STOCHd_14_3_3"]
            vote = pd.Series(0.0, index=df.index)
            vote.loc[(k.values < 20) & (k.values > d.values)] = 1.0
            vote.loc[(k.values > 80) & (k.values < d.values)] = -1.0
            all_votes.append(vote.where(k.notna(), np.nan))

        # 3. CCI
        cci = ta.cci(high, low, close, length=20)
        if cci is not None:
            cci = cci.reindex(df.index)
            vote = pd.Series(0.0, index=df.index)
            vote.loc[cci.values < -100] = 1.0
            vote.loc[cci.values > 100] = -1.0
            all_votes.append(vote.where(cci.notna(), np.nan))

        # 4. ADX
        adx = ta.adx(high, low, close, length=14)
        if adx is not None:
            adx = adx.reindex(df.index)
            adx_val, dmp, dmn = adx["ADX_14"], adx["DMP_14"], adx["DMN_14"]
            vote = pd.Series(0.0, index=df.index)
            vote.loc[(adx_val.values > 20) & (dmp.values > dmn.values)] = 1.0
            vote.loc[(adx_val.values > 20) & (dmn.values > dmp.values)] = -1.0
            all_votes.append(vote.where(adx_val.notna(), np.nan))

        # 5. AO
        ao = ta.ao(high, low)
        if ao is not None:
            ao = ao.reindex(df.index)
            vote = pd.Series(0.0, index=df.index)
            vote.loc[(ao.values > 0) & (ao.values > ao.shift(1).values)] = 1.0
            vote.loc[(ao.values < 0) & (ao.values < ao.shift(1).values)] = -1.0
            all_votes.append(vote.where(ao.notna(), np.nan))

        # 6. Momentum
        mom = ta.mom(close, length=10)
        if mom is not None:
            mom = mom.reindex(df.index)
            vote = pd.Series(0.0, index=df.index)
            vote.loc[mom.values > 0] = 1.0
            vote.loc[mom.values < 0] = -1.0
            all_votes.append(vote.where(mom.notna(), np.nan))

        # 7. MACD
        macd = ta.macd(close, fast=12, slow=26, signal=9)
        if macd is not None:
            macd = macd.reindex(df.index)
            hist = macd["MACDh_12_26_9"]
            vote = pd.Series(0.0, index=df.index)
            vote.loc[hist.values > 0] = 1.0
            vote.loc[hist.values < 0] = -1.0
            all_votes.append(vote.where(hist.notna(), np.nan))

        # 8. Stochastic RSI
        stochrsi = ta.stochrsi(close, length=14, rsi_length=14, k=3, d=3)
        if stochrsi is not None:
            stochrsi = stochrsi.reindex(df.index)
            k = stochrsi["STOCHRSIk_14_14_3_3"]
            vote = pd.Series(0.0, index=df.index)
            vote.loc[k.values < 20] = 1.0
            vote.loc[k.values > 80] = -1.0
            all_votes.append(vote.where(k.notna(), np.nan))

        # 9. Williams %R
        willr = ta.willr(high, low, close, length=14)
        if willr is not None:
            willr = willr.reindex(df.index)
            vote = pd.Series(0.0, index=df.index)
            vote.loc[willr.values < -80] = 1.0
            vote.loc[willr.values > -20] = -1.0
            all_votes.append(vote.where(willr.notna(), np.nan))

        # 10. Bull Bear Power
        ema13 = ta.ema(close, length=13)
        if ema13 is not None:
            ema13 = ema13.reindex(df.index)
            val = (high.values - ema13.values) + (low.values - ema13.values)
            val_s = pd.Series(val, index=df.index)
            vote = pd.Series(0.0, index=df.index)
            vote.loc[(val_s.values > 0) & (val_s.values > val_s.shift(1).values)] = 1.0
            vote.loc[(val_s.values < 0) & (val_s.values < val_s.shift(1).values)] = -1.0
            all_votes.append(vote.where(ema13.notna(), np.nan))

        # 11. Ultimate Oscillator
        uo = ta.uo(high, low, close, fast=7, medium=14, slow=28)
        if uo is not None:
            uo = uo.reindex(df.index)
            vote = pd.Series(0.0, index=df.index)
            vote.loc[uo.values < 30] = 1.0
            vote.loc[uo.values > 70] = -1.0
            all_votes.append(vote.where(uo.notna(), np.nan))

        if not all_votes:
            return pd.Series(0.0, index=df.index)

        return pd.concat(all_votes, axis=1).mean(axis=1)

    @staticmethod
    def calculate_recommend_other(df: pd.DataFrame) -> float:
        series = TechnicalRatings.calculate_recommend_other_series(df)
        return float(series.iloc[-1]) if not series.empty else 0.0

    @staticmethod
    def calculate_recommend_all(df: pd.DataFrame, ma_score: Optional[float] = None, osc_score: Optional[float] = None) -> float:
        if ma_score is None:
            ma_score = TechnicalRatings.calculate_recommend_ma(df)
        if osc_score is None:
            osc_score = TechnicalRatings.calculate_recommend_other(df)
        return (ma_score + osc_score) / 2.0
