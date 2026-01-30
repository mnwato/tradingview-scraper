# Specification: Async Streamer V1

## 1. Goal
Transition the WebSocket streamer from a synchronous, blocking implementation to a modern, `asyncio`-based architecture. This allows for concurrent streaming of multiple assets and seamless integration into the project's asynchronous quantitative pipeline.

## 2. Technical Requirements

### A. Asynchronous WebSocket Handling
- **Library**: `aiohttp.ClientSession.ws_connect`.
- **Concurrency**: Use `asyncio.create_task` for background heartbeat maintenance.
- **Message Parsing**: Implement non-blocking parsing of the custom `~m~<length>~m~` TradingView framing.

### B. Async Streamer Interface
- **Generator**: `get_data()` must be an `async generator` yielding parsed JSON packets.
- **Initialization**: Async initialization of quote and chart sessions.
- **Parity**: Must support indicators, multiple timeframes, and symbol validation identical to the synchronous `Streamer`.

### C. Error Handling & Recovery
- **Non-blocking Retries**: Use exponential backoff with `asyncio.sleep`.
- **State Persistence**: The handler must track active subscriptions to re-initialize them automatically upon reconnection.

## 3. Success Criteria
- [ ] `AsyncStreamer` can maintain a connection for at least 5 minutes without dropping.
- [ ] Heartbeats are handled in the background without blocking data consumption.
- [ ] Multiple symbols can be streamed concurrently in a single event loop.
- [ ] Unit tests pass with >80% coverage.
