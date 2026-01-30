# Research Report: Lakehouse Data Quality & Gap Management

## 1. Executive Summary
This research focuses on maintaining the integrity of the local Data Lakehouse. We have implemented automated gap detection and repair mechanisms to ensure that historical datasets are continuous and reliable for backtesting.

## 2. Gap Detection Methodology
The `LakehouseStorage.detect_gaps()` method scans the stored time-series for missing intervals.
*   **Threshold:** A gap is defined as any difference between consecutive timestamps greater than **1.5x the expected interval**.
*   **Market Awareness:** While crypto is 24/7, traditional markets have expected gaps. Current detection is optimized for crypto; future iterations will integrate market calendars to ignore structural gaps (weekends/holidays).

## 3. Automated Repair Strategy (Gap Filler)
The `PersistentDataLoader.repair()` method automates the recovery of missing data:
1.  **Identification:** Gaps are located using the detection engine.
2.  **Lookback Calculation:** For each gap, the system calculates the exact `numb_price_candles` required to reach back from `now` to the start of the gap.
3.  **Targeted Ingestion:** The `Streamer` fetches the required depth, and `LakehouseStorage` merges the results using timestamp-based deduplication.
4.  **Limits:** Repairs are limited by the API's hard cap (~8,500 candles). Gaps deeper than this limit require external data or manual intervention.

## 4. Verification & Testing
*   **Unit Tests:** `tests/test_lakehouse_storage.py` verifies core storage operations, including deduplication and range loading.
*   **Demonstration:** A successful demo (`scripts/demo_gap_management.py`) proved that manually introduced gaps (deleting middle records) are correctly identified and 100% repaired in seconds.

## 5. Conclusion
The combination of `detect_gaps` and `repair` transforms the local lakehouse from a simple cache into a self-healing historical database. This is a critical component for institutional-grade research where data continuity is paramount.
