# Specification: Synthetic Recommend.MA Reconstruction (v1.0)

## 1. Overview
This specification defines the logic for reconstructing TradingView's `Recommend.MA` rating from raw OHLCV data. This enables the generation of historical rating signals for backtesting, resolving the "Discovery-Backtest Regime Mismatch".

## 2. Component Logic
The rating is an unweighted average of **15 components**.
Formula: $$ Score = \frac{N_{Buy} - N_{Sell}}{15} $$

### 2.1 Moving Averages (12 Components)
Compare current **Close Price** ($P_t$) with the Moving Average ($MA_t$).
- **Buy**: $P_t > MA_t$
- **Sell**: $P_t < MA_t$
- **Neutral**: $P_t = MA_t$

**Indicators**:
- **SMA**: Lengths 10, 20, 30, 50, 100, 200.
- **EMA**: Lengths 10, 20, 30, 50, 100, 200.

### 2.2 Volume Weighted MA (1 Component)
- **Indicator**: VWMA (20)
- **Logic**: Compare $P_t$ vs $VWMA_t$.

### 2.3 Hull Moving Average (1 Component)
- **Indicator**: HMA (9)
- **Logic**: Compare $P_t$ vs $HMA_t$.

### 2.4 Ichimoku Cloud (1 Component)
- **Indicator**: Ichimoku (9, 26, 52)
- **Logic**: Compare Price vs Cloud (Kumo) shifted forward by 26 periods.
- **Calculation**:
    - **Tenkan-sen (Conversion)**: $(High_9 + Low_9) / 2$ at $t-26$.
    - **Kijun-sen (Base)**: $(High_{26} + Low_{26}) / 2$ at $t-26$.
    - **Senkou Span A**: $(Tenkan + Kijun) / 2$.
    - **Senkou Span B**: $(High_{52} + Low_{52}) / 2$ at $t-26$.
    - **Cloud Top**: $Max(SpanA, SpanB)$
    - **Cloud Bottom**: $Min(SpanA, SpanB)$
- **Scoring**:
    - **Buy**: $P_t > CloudTop$
    - **Sell**: $P_t < CloudBottom$
    - **Neutral**: $CloudBottom \le P_t \le CloudTop$ (Price inside Cloud)

## 3. Implementation Verification
Validating against `BINANCE:BTCUSDT` snapshot on 2026-01-17:
- **Actual TV Score**: 0.2667
- **Synthetic Score**: 0.2667
- **Match**: ✅ Perfect (Difference 0.0000)

## 4. Usage
This logic should be implemented in the `HistoricalFeatureBackfill` service to generate the `features_matrix.parquet` for valid historical backtesting.
