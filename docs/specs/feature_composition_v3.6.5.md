# Feature Composition & Signal Design (v3.6.5)

## 1. Overview
The TradingView Scanner provides high-level composite signals (`Recommend.All`, `Recommend.MA`, `Recommend.Other`) derived from an ensemble of underlying technical indicators. Understanding their composition is critical for designing orthogonal alpha strategies.

## 2. Signal Decomposition

### 2.1 Moving Averages Rating (`Recommend.MA`)
**Purpose**: Measures Trend Strength & Direction.
**Composition**: A weighted consensus of Trend Indicators across multiple timeframes.
**Components**:
- **Simple Moving Averages (SMA)**: Lengths 10, 20, 30, 50, 100, 200.
- **Exponential Moving Averages (EMA)**: Lengths 10, 20, 30, 50, 100, 200.
- **Ichimoku Cloud**: Base Line (9), Conversion Line (26), Leading Span B (52).
- **Volume Weighted MA (VWMA)**: Length 20.
- **Hull Moving Average (HMA)**: Length 9.

**Logic**:
- $Score = \frac{Buy - Sell}{Total}$
- Range: [-1.0 (Strong Sell) to +1.0 (Strong Buy)].

### 2.2 Oscillators Rating (`Recommend.Other`)
**Purpose**: Measures Mean Reversion & Overbought/Oversold conditions.
**Composition**: A weighted consensus of 11 Oscillators.
**Components**:
- **RSI (14)**: Relative Strength Index. Classic momentum/overbought-oversold.
- **Stochastic (%K 14, %D 3)**: Momentum measure. Uses `smooth_k=3` implicitly in TV.
- **CCI (20)**: Commodity Channel Index. Deviation from average price.
- **ADX (14, 14)**: Average Directional Index. DI length 14, ADX smoothing 14. Uses +DI/-DI for bias.
- **AO**: Awesome Oscillator. Momentum comparing recent MAs.
- **Momentum (10)**: Rate of price change.
- **MACD (12, 26, 9)**: Moving Average Convergence Divergence.
- **Stochastic RSI (3, 3, 14, 14)**: Sensitive short-term oscillator of RSI.
- **Williams %R (14)**: Position in recent High-Low range.
- **Bull Bear Power (13)**: Buying vs Selling pressure relative to EMA.
- **Ultimate Oscillator (7, 14, 28)**: Weighted sum of short/medium/long momentum.

**Logic**:
- $Score = \frac{Buy - Sell}{11}$
- Range: [-1.0 (Strong Sell) to +1.0 (Strong Buy)].

### 2.3 Composite Rating (`Recommend.All`)
**Purpose**: General Health Score.
**Composition**: A linear combination of the Trend and Oscillator ratings.
**Formula** (Empirically Derived):
$$ \text{Recommend.All} \approx W_{MA} \times \text{Recommend.MA} + W_{Osc} \times \text{Recommend.Other} $$
- **Typical Weights**: $W_{MA} \approx 0.6$, $W_{Osc} \approx 0.4$.
- **Bias**: Slightly favors Trend Following.

## 3. Alpha Strategy Implications

### 3.1 "Rating All" Strategies
- **Profile**: Hybrid Trend-Following with Mean-Reversion filters.
- **Usage**: General-purpose "Core" allocation.
- **Ranker**: `MPSRanker` (Ensemble) or `SignalRanker(Recommend.All)`.

### 3.2 "Rating MA" Strategies
- **Profile**: Pure Trend Following.
- **Usage**: Directional momentum capture.
- **Ranker**: `SignalRanker(Recommend.MA)` or `MPSRanker` with `dominant_signal="recommend_ma"`.
- **Direction**:
    - Long: Descending (High Score).
    - Short: Ascending (Low Score).

### 3.3 "Rating Other" Strategies (Future)
- **Profile**: Mean Reversion / Swing Trading.
- **Usage**: Catching tops/bottoms in range-bound markets.
- **Ranker**: `SignalRanker(Recommend.Other)`.

## 4. Multi-Timeframe (MTF) Expansion
To increase signal fidelity, strategies should verify alignment across adjacent timeframes:
- **Confirmation**: `Recommend.MA_1d > 0` AND `Recommend.MA_4h > 0`.
- **Divergence**: `Recommend.MA_1d > 0` AND `Recommend.Other_4h < 0` (Trend up, but short-term overbought).

This logic is enabled by the schema expansion in v3.6.5 (126 columns).

## 5. Implementation Reference
The official Python implementation of these ratings is available in:
- **Module**: `tradingview_scraper.utils.technicals`
- **Class**: `TechnicalRatings`
- **Methods**: `calculate_recommend_ma`, `calculate_recommend_other`, `calculate_recommend_all`
- **Dependencies**: `pandas-ta-classic`

## 6. Performance Features (v3.6.6)
The feature schema includes high-resolution performance metrics for all supported timeframes (1m to 1M).

**Important**: Standard `Perf.*` fields (e.g., `Perf.W`, `Perf.1M`) are global and **do not** accept timeframe suffixes. Instead, use the `change` metric for timeframe-specific returns.

### 6.1 Available Metrics (Suffix-Compatible)
These metrics can be suffixed (e.g., `change_5m`, `volume_1h`):
- `change_{interval}`: Percent price change.
- `change_abs_{interval}`: Absolute price change.
- `gap_{interval}`: Gap percent.
- `volume_{interval}`: Volume.
- `close_{interval}`, `high_{interval}`, `low_{interval}`, `open_{interval}`: OHLC prices.

### 6.2 Global Performance Metrics (No Suffix)
These metrics are available only in the base timeframe (usually Daily):
- `Perf.W`, `Perf.1M`, `Perf.3M`, `Perf.6M`, `Perf.Y`, `Perf.3Y`, `Perf.5Y`, `Perf.All`, `Perf.YTD`.
- `Volatility.D`, `Volatility.W`, `Volatility.M`.

These metrics enable granular "Flash Crash" detection (e.g. `change_5m < -0.05`) and "Volume Surge" analysis.
