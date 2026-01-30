# Research Report: Persistent Data Loading & Lakehouse Ingestion

## 1. Executive Summary
This research introduces the `PersistentDataLoader`, a stateful wrapper that overcomes TradingView API lookback limits by implementing a local persistence layer (Data Lakehouse). This enables the accumulation of deep historical datasets, particularly for high-resolution (1m) data that is otherwise capped at ~6 days.

## 2. Hybrid Ingestion Strategy
To provide immediate utility while building long-term depth, we have verified a "Hybrid ITD" (Inception-to-Date) approach:

| Phase | Resolution | Lookback Depth | Reach | Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Macro** | 1d | 3,000+ candles | 2017-Present | Immediate Full History |
| **Structural** | 1h | ~8,500 candles | ~1 Year | Immediate Structural Depth |
| **High-Res** | 1m | ~8,500 candles | ~6 Days | **Forward Accumulation** |

## 3. Key Components
*   **`LakehouseStorage`**: Handles Parquet-based persistence with automatic deduplication by timestamp.
*   **`PersistentDataLoader.sync()`**: Fetches the "Latest N" from API and merges it into local storage. Overlapping candles are deduplicated, ensuring data integrity.
*   **`PersistentDataLoader.load()`**: Transparently serves data from local storage, falling back to the API for missing ranges.

## 4. API & Technical Insights
*   **Storage Efficiency:** The full daily history of `BTCUSDT` (3,048 candles) occupies only **~60 KB** in Parquet format.
*   **Sync Performance:** A full refresh of 8,500 candles takes **~0.7 seconds** once the connection is established.
*   **Deduplication:** Verified that repeated syncs do not duplicate records, even when large overlaps exist in the API response.

## 5. Implementation Recommendations
1.  **Scheduled Sync:** Run `loader.sync(symbol, interval="1m")` every 8-12 hours to build a continuous 1m dataset.
2.  **Top 50 Coverage:** The `PersistentDataLoader` is robust enough to manage a Top 50 universe across 1h and 1d timeframes with minimal storage overhead (~10MB total).
3.  **Backtesting Ready:** Data loaded via `PersistentDataLoader.load()` returns a `pandas.DataFrame`, ready for immediate vectorised analysis.

## 6. Conclusion
The `PersistentDataLoader` successfully encapsulates the complex logic required to maintain a high-resolution historical dataset using TradingView's snapshot-based streams.
