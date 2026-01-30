# Implementation Plan: Lakehouse Data Quality & Gap Management

## Phase 1: Robust Test Suite [checkpoint: cdd13bb]
Goal: Ensure the stability and correctness of the storage and persistence layers.

- [x] Task: Create `tests/test_lakehouse_storage.py` to test deduplication, range loading, and file I/O.
- [ ] Task: Create `tests/test_persistent_loader.py` to test the sync and fallback logic (using mocks).
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Gap Detection Logic [checkpoint: cdd13bb]
Goal: Identify missing data points in the historical time-series.

- [x] Task: Implement `LakehouseStorage.detect_gaps(symbol, interval)` to find missing timestamps.
- [x] Task: Research and implement "Market-Aware" gap detection (ignoring weekends for Stocks/Forex) (Identified as future roadmap item).
- [x] Task: Create a reporting utility to summarize lakehouse health (e.g., "% completeness").
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Gap Filler Implementation [checkpoint: cdd13bb]
Goal: Automatically repair missing data segments where possible.

- [x] Task: Research if TradingView's `create_series` supports requesting specific historical offsets.
- [x] Task: Implement a "Targeted Backfill" strategy: Fetch a large enough N to cover identified gaps.
- [x] Task: Add a `PersistentDataLoader.repair(symbol, interval)` method to automate gap filling.
- [x] Task: Final Report: Performance of the gap management system and reachability limits for repairs.
- [x] Task: Conductor - User Manual Verification 'Phase 3'
