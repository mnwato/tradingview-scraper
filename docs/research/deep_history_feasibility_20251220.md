# Research Report: Deep Historical Data Lookback & Inception Feasibility

## 1. Executive Summary
This research investigates the "Genesis Reach" of the TradingView WebSocket API for `BINANCE:BTCUSDT`. We aimed to determine if a full history from Binance's inception (Aug 2017) is reachable and at what resolution.

## 2. API Depth Limits (Unauthorized Tier)
Testing conducted on 2025-12-20 revealed significant "Hard Limits" on the number of candles served per request:

| Interval | Requested | Received | Oldest Reachable | Reach Years |
| :--- | :--- | :--- | :--- | :--- |
| **1d** | 5000 | **3048** | **2017-08-17** | ~8.3 years (Full History) |
| **1h** | 10000 | **8495** | **2025-01-01** | ~1 year |
| **1m** | 10000 | **8580** | **2025-12-15** | ~6 days |

### Key Observation:
*   **Daily (1d):** Provides 100% coverage since Binance inception. Ideal for macro structural backtesting.
*   **Intraday (1h/1m):** Severely limited. A "Hard Cap" of approximately **8,500 candles** exists for intraday series on this tier.

## 3. Dataset Size Estimation
To build a full-history Data Lakehouse for `BTCUSDT`, the estimated storage requirements are:

| Resolution | Total Candles | Est. CSV Size | Est. Parquet Size |
| :--- | :--- | :--- | :--- |
| 1m | 4,389,115 | 418.58 MB | 83.72 MB |
| 1h | 73,151 | 6.98 MB | 1.40 MB |
| 1d | 3,047 | 0.29 MB | 0.06 MB |

*Calculations based on 100 bytes/row (CSV) and 20 bytes/row (Parquet).*

## 4. Feasibility for Data Lakehouse
Building a 100% complete high-resolution (1m) lakehouse **from inception is NOT possible** using only the current WebSocket's "Latest N" retrieval.

### Proposed Accumulation Strategy:
1.  **Macro Baseline:** Ingest full 1d history immediately (3,048 candles).
2.  **Structural Baseline:** Ingest the last ~1 year of 1h history (8,495 candles).
3.  **Forward Accumulation:** For 1m data, implement a **"Sliding Window Ingestor"** that fetches 500 candles every 8 hours and appends to an Iceberg/Parquet table. Over time, this will build the high-res history that the API currently cuts off.

## 5. Conclusion
The API is excellent for structural backtesting (Daily/Hourly) and real-time monitoring. However, for a high-resolution (1m) historical lakehouse starting from 2017, external data sources or long-term forward accumulation are required.
