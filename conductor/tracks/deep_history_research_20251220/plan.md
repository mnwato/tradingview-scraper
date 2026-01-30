# Implementation Plan: Deep Historical Data Lookback & Inception Research

## Phase 1: Dataset Estimation & API Limits Research [checkpoint: b65485f]
Goal: Estimate the total size of Binance `BTCUSDT` data from inception and research API depth.

- [x] Task: Calculate total candle counts for 1m, 1h, and 1d intervals from Aug 2017 to Dec 2025.
- [x] Task: Estimate storage size (CSV vs. Parquet) for the full "Genesis-to-Now" dataset.
- [x] Task: Research the TradingView "Hard Limit" for lookback depth on the free tier for 1m and 1h intervals (Found ~8,500 candle cap).
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Deep Lookback Connectivity Testing [checkpoint: b65485f]
Goal: Proactively test the WebSocket's ability to serve very old data.

- [x] Task: Implement a "Genesis Walkback" script that requests 5000+ candles for various timeframes.
- [x] Task: Verify the oldest reachable timestamp for `BINANCE:BTCUSDT` at 1h and 1d resolution (1d: 2017-08-17, 1h: 2025-01-01).
- [x] Task: Analyze data quality and gap frequency in extremely old data (pre-2020) (Daily data is high quality since inception).
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Final Feasibility & Storage Report [checkpoint: b65485f]
Goal: Deliver a comprehensive report on building a full-history crypto data lake.

- [x] Task: Final Report: Is a 100% complete Binance history reachable via this library? (Only for 1d timeframe).
- [x] Task: Document the "Cost-Benefit" analysis of high-res (1m) vs. structural (1h) deep history.
- [x] Task: Propose a strategy for reliable "Inception-to-Date" (ITD) data synchronisation (Sliding window forward accumulation).
- [x] Task: Conductor - User Manual Verification 'Phase 3'