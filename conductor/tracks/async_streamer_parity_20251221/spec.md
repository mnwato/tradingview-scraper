# Specification: Async Streamer Feature Parity

## 1. Goal
Ensure that `AsyncStreamer` provides the same structured data output and operational capabilities as the original synchronous `Streamer` class. This includes converting raw WebSocket packets into friendly dictionaries and supporting automated data collection/export.

## 2. Technical Requirements

### A. Data Serialization
- Implement `_serialize_ohlc` and `_serialize_indicator` logic in `AsyncStreamer`.
- The output format must match the synchronous version exactly:
    - **OHLC**: `{"index": ..., "timestamp": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}`
    - **Indicator**: `{"index": ..., "timestamp": ..., "0": ..., "1": ...}` (mapped by study ID).

### B. Functional Parity
- **Export Support**: Integrate `save_json_file` and `save_csv_file` logic into the async stream loop.
- **Batch Collection**: Implement a `collect(n_candles)` method that returns a final dictionary of OHLC and indicator data after reaching the requested count, matching the `Streamer.stream()` behavior when `export_result=True`.

### C. Structural Consolidation
- Extract shared serialization logic from `streamer.py` and `streamer_async.py` into a central `tradingview_scraper/symbols/stream/utils.py` module to prevent logic drift.

## 3. Success Criteria
- `AsyncStreamer` output is bit-identical to `Streamer` output for the same WebSocket packets.
- `AsyncStreamer.collect()` successfully exports files and returns structured summaries.
- No duplicated serialization code exists in the `stream/` directory.
