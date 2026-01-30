# Specification: Price Stream Resilience & Performance

## Overview
This specification details the improvements to the `RealTimeData` class in `tradingview_scraper/symbols/stream/price.py`. The goals are to eliminate artificial latency, implement robust heartbeat monitoring, and ensure automatic recovery from stalled connections.

## Requirements

### 1. Performance
- **Zero Artificial Latency**: The `sleep(1)` inside the packet receiving loop must be removed.
- **Blocking I/O with Timeout**: The WebSocket `recv()` call should be blocking but governed by a `ws_timeout` to prevent indefinite hangs.

### 2. Heartbeat Management (Idle Detection)
- **Idle Packet Limit**: The system must track consecutive "idle" packets (heartbeats).
- **Configurability**:
    - `idle_packet_limit`: Number of consecutive heartbeats before triggering a reconnect (default: 5).
    - `ws_timeout`: WebSocket timeout in seconds (default: 15.0).
- **Counter Reset**: Any valid data packet (JSON) must reset the idle packet counter to zero.
- **Handshake-Safe Counter Start**: The idle packet counter must not start until at least one non-heartbeat data packet has been received (avoids false timeouts during session negotiation).

### 3. Resilience & Reconnection
- **Automatic Recovery**: Upon reaching the `idle_packet_limit` or encountering a `WebSocketConnectionClosedException`, the system must automatically attempt to reconnect.
- **Subscription Persistence**: Reconnections must re-subscribe to the original symbols and restore the previous session state (quote/chart sessions).
- **Backoff**: Implement a short delay between reconnection attempts to avoid hammering the server.

### 4. Logging
- **Module-level Logging**: Replace `logging.basicConfig` with `logging.getLogger(__name__)`.
- **Heartbeat Visibility**: Heartbeats should be logged at `DEBUG` level. Reconnections and idle triggers should be logged at `WARNING` level.

## Implementation Details

### Class: `RealTimeData`
- **Updated `__init__`**:
    - Accept `idle_packet_limit` and `ws_timeout`.
    - Support environment variables: `STREAMER_IDLE_PACKET_LIMIT`, `STREAMER_WS_TIMEOUT`.
- **New Method: `_setup_connection()`**:
    - Handles `create_connection`.
    - Initializes sessions (`set_auth_token`, etc.).
- **Refactored `get_data()`**:
    - Main loop for receiving and yielding data.
    - Handles heartbeats and increments idle counter.
    - Breaks loop on idle limit to trigger retry in outer scope.

## Related: `Streamer` End-of-History
- `Streamer.stream()` includes an additional collector loop that returns partial OHLC once it detects "no new OHLC/indicator updates" after at least one payload (see `tradingview_scraper/symbols/stream/streamer.py`).
