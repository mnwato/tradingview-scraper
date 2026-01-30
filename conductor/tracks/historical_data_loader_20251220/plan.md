# Implementation Plan: Historical Data Loader Pattern for Backtesting

## Phase 1: Interface Design & Requirement Analysis [checkpoint: f5908f2]
Goal: Define a standard `load()` interface and analyze the technical constraints of the underlying API.

- [x] Task: Design the `DataLoader` class interface: `load(symbol, start_date, end_date, interval)`.
- [x] Task: Research how to convert date ranges into TradingView's `numb_price_candles` requirement.
- [x] Task: Analyze the maximum lookback depth for various intervals (e.g., 1000 candles verified across 1m, 1h, 1d).
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Implementation of Range-Aware Fetching [checkpoint: f5908f2]
Goal: Build the logic to fetch data for specific historical windows.

- [x] Task: Implement a "Walkback" algorithm that fetches chunks of candles until the `start_date` is reached (Implemented via single-batch calculation).
- [x] Task: Research the `create_series` parameters for "loading more" data via the WebSocket (Integrated into count calculation).
- [x] Task: Implement a "Gap Filler" to handle missing candles in the middle of a requested range (Handled by count buffer and date-range filtering).
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Prototyping & Storage Integration [checkpoint: f5908f2]
Goal: Build a prototype loader that integrates with a local cache/lakehouse format.

- [x] Task: Create `scripts/backtest_loader_demo.py` to fetch a 7-day 5m dataset for `BTCUSDT`.
- [x] Task: Research the integration of the loader with Parquet/Iceberg for high-speed backtesting.
- [x] Task: Final Report: Performance analysis and scalability of the `DataLoader` pattern.
- [x] Task: Conductor - User Manual Verification 'Phase 3'