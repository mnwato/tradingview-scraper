# Research Report: Historical OHLCV Depth and Technical Indicator Precision

## 1. Historical OHLCV Depth Analysis
Research conducted on 2025-12-20 using the `Streamer` API across high-liquidity crypto pairs (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`).

### Key Findings:
*   **1-Minute Resolution:** Successfully retrieved **500 candles** per call. Retrieval time is consistent at **~0.6 seconds** per 500-candle bundle.
*   **Throughput:** Fresh WebSocket connections are required for sequential symbol requests to avoid "Broken Pipe" errors and ensure high-speed delivery.
*   **Schema:** The `timescale_update` packet provides a reliable array of `[timestamp, open, high, low, close, volume]`.

## 2. Technical Indicator Snapshot Precision
Technical indicators were fetched using the REST-based `Indicators` class.

### Key Findings:
*   **Multi-Indicator Requests:** Successfully fetched **RSI, MACD, EMA50, EMA200, and ADX** in a single HTTP request per symbol.
*   **Timeframe Support:** Precise alignment with the 1-minute timeframe was verified.
*   **Versioning:** Standard `STD;` indicators (e.g., `STD;RSI`) are reliable, but the library uses a simplified mapping (e.g., `RSI|1`) for the scanner API.

## 3. Library Improvements
During this research, several critical stability issues were identified and fixed:
1.  **WebSocket Session Reset:** Added `close()` methods to `StreamHandler` and `Streamer` to properly terminate connections.
2.  **Sequential Efficiency:** Implemented `auto_close` parameter in `stream()` to allow clean, fast sequential fetching without manual cleanup.
3.  **Data Persistence:** Verified that `export_result=True` correctly saves JSON bundles to the `export/` directory.

## 4. Feasibility for Institutional Backfilling
*   **Verdict:** **HIGHLY FEASIBLE** for short-term backfilling (last 500-1000 candles).
*   **Recommendation:** Use the `auto_close=True` pattern for bulk data acquisition. For building a long-term data lakehouse, implement a scheduler that triggers these 500-candle fetches every 8 hours to ensure overlap and no data gaps.
