# Design Plan: Multi-Timeframe Technicals Ingestion (2026-01-17)

## 1. Objective
Enhance the feature ingestion pipeline to capture TradingView technical indicators across multiple timeframes (1m to 1M), matching the app's capabilities. This enriches the feature set for granular alpha detection (e.g., MTF alignment).

## 2. Supported Intervals
We will map readable intervals to TradingView suffixes:
- `1m`: `"1"`
- `3m`: `"3"`
- `5m`: `"5"`
- `15m`: `"15"`
- `30m`: `"30"`
- `1h`: `"60"`
- `2h`: `"120"`
- `4h`: `"240"`
- `1d`: `""` (Default)
- `1W`: `"1W"`
- `1M`: `"1M"`

## 3. Targeted Features
To avoid API limits while maximizing value, we target key momentum and oscillation fields:
- `Recommend.All` (Composite Rating)
- `Recommend.MA` (Moving Average Rating)
- `Recommend.Other` (Oscillator Rating)
- `RSI`
- `ADX`
- `AO` (Awesome Oscillator)
- `CCI20`
- `MACD.macd`
- `MACD.signal`
- `Stoch.K`
- `Stoch.D`

## 4. Implementation

### 4.1 Update `scripts/services/ingest_features.py`
- Modify `FeatureIngestionService.fetch_technicals_single`.
- Construct a dynamic list of fields: `{field}|{suffix}`.
- Map response keys back to structured schema: `{field}_{interval}` (e.g., `rsi_4h`, `recommend_all_1m`).
- Handle API request construction (ensure URL length is managed or batched if needed, though typically ~200 fields is accepted).

### 4.2 Data Schema
The output Parquet schema will expand from ~15 columns to ~100+ columns.
Parquet handles wide tables efficiently.

## 5. Execution
- Apply changes to `scripts/services/ingest_features.py`.
- Run a test ingestion on a small candidate set.
