# Implementation Plan: Async Streamer Feature Parity
**Track ID**: `async_streamer_parity_20251221`
**Status**: Planned

## 1. Objective
Achieve 100% logic parity between the legacy synchronous `Streamer` and the new `AsyncStreamer`, specifically regarding data serialization, structured output, and file export.

## 2. Phases

### Phase 1: Data Serialization Parity [checkpoint: 060f513]
Goal: Transform raw WebSocket packets into structured dictionaries.
- [x] Task: Implement OHLC and Indicator serialization logic in `AsyncStreamer`. 51a91cb
- [x] Task: Update `get_data()` to yield formatted data. 2114916
- [x] Task: Verify parity via unit tests comparing sync/async dictionary output. 060f513

### Phase 2: Functional Parity [checkpoint: 20200b4]
Goal: Implement one-shot collection and export.
- [x] Task: Implement `export_result` support (persistence to JSON/CSV). 20200b4
- [x] Task: Implement `collect(n_candles)` helper method for batch retrieval. 20200b4

### Phase 3: Structural Consolidation [checkpoint: b8df62a]
Goal: Clean up duplicate logic.
- [x] Task: Move shared parsing logic to `tradingview_scraper/symbols/stream/utils.py`. b8df62a
- [x] Task: Refactor both screeners to use centralized utilities. b8df62a

### Phase 4: Validation [checkpoint: ddfb03d]
- [x] Task: Final parity audit and benchmark. ddfb03d
- [x] Task: Final Report. ddfb03d
