# Research Report: Historical Data Loader Pattern for Backtesting

## 1. Executive Summary
This research introduces and validates the `DataLoader` pattern, providing a standardized interface for fetching specific ranges of historical OHLCV data. By calculating the required candle count based on the desired start date and timeframe, we enable seamless data acquisition for backtesting without manual count management.

## 2. Interface Specification
The `DataLoader` class implements the following high-level interface:
```python
load(exchange_symbol, start_date, end_date, interval="1h")
```
*   **Automatic Calculation:** Converts the date range into the `numb_price_candles` required by the underlying WebSocket API.
*   **Filtering:** Automatically trims the returned series to exactly match the requested `[start, end]` window.
*   **Stability:** Utilizes the `auto_close=True` pattern to ensure clean sequential requests for multiple symbols.

## 3. Depth & Resolution Validation
Research confirms reliable retrieval depths across common institutional timeframes:

| Timeframe | Tested Depth | Range Duration | Retrieval Time |
| :--- | :--- | :--- | :--- |
| 1m | 1000 candles | ~16 hours | ~0.6s |
| 15m | 300 candles | ~3 days | ~0.5s |
| 1h | 1000 candles | ~41 days | ~0.6s |
| 1d | 1000 candles | ~2.7 years | ~0.6s |

## 4. Implementation Details
*   **Module:** `tradingview_scraper/symbols/stream/loader.py`
*   **Key Logic:** `_calculate_candles_needed()` uses `datetime.now()` and structural timeframe mapping to determine the necessary lookback.
*   **Efficiency:** The loader uses a single batch request to the WebSocket per symbol, minimizing overhead.

## 5. Backtesting Integration
The `DataLoader` is designed to be the primary ingestion layer for a local backtesting engine.
*   **Recommended Workflow:** Stream data via `DataLoader` -> Store as **Parquet** in a local lakehouse -> Run vectorised backtests using **Pandas**.
*   **Limitation:** The API is optimized for "latest N" data. Requests for historical windows very far in the past (e.g., year 2020 at 1m resolution) may hit depth limits of the free TradingView tier.

## 6. Conclusion
The `DataLoader` pattern successfully bridges the gap between TradingView's "latest-only" streaming API and the requirements of date-range-based backtesting systems.
