# TradingView Features Catalog

## 1. Overview
This catalog defines the standard signal features ingested from TradingView's Scanner API. These features drive the "Natural Selection" and "Strategy Synthesis" engines.

## 2. Rating Signals (The "Recommend" Family)
These are composite scores ranging from `-1.0` (Strong Sell) to `1.0` (Strong Buy).

| Feature Name | Description | Components |
| :--- | :--- | :--- |
| **`Recommend.All`** | Global composite rating. | Weighted average of `Recommend.MA` and `Recommend.Other`. |
| **`Recommend.MA`** | Moving Average rating. | Aggregation of SMA/EMA (10, 20, 50, 100, 200). |
| **`Recommend.Other`** | Oscillator rating. | Aggregation of RSI, Stoch, CCI, ADX, AO, Momentum, MACD. |

### Interpretation
- `0.5 to 1.0`: **Strong Buy**
- `0.1 to 0.5`: **Buy**
- `-0.1 to 0.1`: **Neutral**
- `-0.5 to -0.1`: **Sell**
- `-1.0 to -0.5`: **Strong Sell**

## 3. Technical Indicators (Raw)

| Feature Name | Description | Typical Range |
| :--- | :--- | :--- |
| **`RSI`** | Relative Strength Index (14). | 0 - 100 (Overbought > 70, Oversold < 30). |
| **`ADX`** | Average Directional Index (14). | 0 - 100 (Trend Strength > 25). |
| **`CCI20`** | Commodity Channel Index (20). | -200 to +200. |
| **`Stoch.K`** | Stochastic %K. | 0 - 100. |
| **`Stoch.D`** | Stochastic %D. | 0 - 100. |
| **`MACD.macd`** | MACD Line. | Unbounded. |
| **`MACD.signal`** | MACD Signal Line. | Unbounded. |
| **`AO`** | Awesome Oscillator. | Unbounded. |
| **`ATR`** | Average True Range. | Price units. |

## 4. Derived Metrics

| Feature Name | Description |
| :--- | :--- |
| **`Volatility.D`** | Daily Volatility (Standard Deviation of returns). |
| **`Perf.W`** | Weekly Performance (%). |
| **`Perf.1M`** | Monthly Performance (%). |
| **`Perf.3M`** | Quarterly Performance (%). |
| **`Perf.YTD`** | Year-to-Date Performance (%). |

## 5. Feature Store Integration
*   **Path**: `data/lakehouse/features/tv_technicals_1d.parquet`
*   **Ingestion**: Daily via `scripts/services/ingest_features.py`.
*   **Availability**: T+0 (Snapshot at ingestion time).
