# Implementation Plan: Async Streamer V1
**Track ID**: `async_streamer_v1_20251221`
**Status**: Planned

## 1. Objective
Migrate the WebSocket streamer to a fully asynchronous architecture using `aiohttp`. This will enable non-blocking real-time data streaming and better integration with the async pipeline.

## 2. Phases

### Phase 1: Async WebSocket Core
Goal: Implement the low-level async connection and heartbeat logic.
- [x] Task: Create `tradingview_scraper/symbols/stream/stream_handler_async.py` (AsyncStreamHandler). fa51120
- [x] Task: Implement background heartbeat task in `AsyncStreamHandler`. 5cef5d7
- [x] Task: Implement async message framing and session initialization. 5cef5d7

### Phase 2: Async Streamer Implementation
Goal: Implement the user-facing async streamer interface.
- [x] Task: Create `tradingview_scraper/symbols/stream/streamer_async.py` (AsyncStreamer). 21dd2d3
- [x] Task: Implement `.get_data()` as an async generator. 21dd2d3
- [x] Task: Implement `.stream()` method with parity for indicators and symbol validation. 21dd2d3

### Phase 3: Resilience & Recovery
Goal: Ensure robust operation and state recovery.
- [x] Task: Implement `AsyncRetryHandler` using `asyncio.sleep`. 98b4cf8
- [x] Task: Implement state-restoration logic (re-subscription) after reconnections. 446f7ad

### Phase 4: Validation
- [x] Task: Create unit tests for `AsyncStreamHandler` and `AsyncStreamer`. 2b7c268
- [x] Task: Add an async stream example to `examples/`. f806df7
- [x] Task: Final Report. d191ada
