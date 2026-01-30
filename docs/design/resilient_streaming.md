# Design Document: Resilient Market Data Streaming

## 1. Overview
The WebSocket-based streaming engine (`RealTimeData`) is designed for low-latency, resilient ingestion of market data from TradingView. This document details the mechanisms for handling network instability, silent connection failures, and batched data processing.

## 2. Heartbeat & Idle Management
WebSocket connections can become "zombies" where the TCP socket remains open but the data stream has stalled. The system uses a heartbeat-based idle detection mechanism.

### 2.1 Idle Packet Detection
- **Mechanism**: The system tracks the number of consecutive **Heartbeat (`~h~`)** packets received without an interleaved data packet.
- **Limit**: Reconnection is triggered after **5 consecutive heartbeats**.
- **Counter Reset**: Any successfully parsed JSON data packet resets the idle counter to zero.
- **Log Level**: Heartbeats are logged at `DEBUG` level to minimize noise.

### 2.2 Echo Protocol
To maintain the connection, the client must echo heartbeats back to the server.
- **Standard**: The client responds with the exact heartbeat ID received (e.g., `~h~123`).
- **Processing**: Heartbeats are intercepted and handled at the lowest level of the `get_data` loop to ensure they don't reach the business logic.

## 3. Latency Optimization
To ensure true real-time performance, the ingestion loop is optimized for high-frequency bursts.

### 3.1 Elimination of Artificial Latency
- **Removal of `sleep(1)`**: Legacy implementations used a 1-second sleep to prevent high CPU usage. This has been removed in favor of Make's blocking `ws.recv()` call with a timeout.
- **Batched Processing**: TradingView often sends multiple messages in a single WebSocket frame. The system uses regex splitting (`~m~\d+~m~`) to process all sub-packets in a single frame immediately.

## 4. Automated Recovery
Connection failures are handled by a multi-layered retry strategy.

### 4.1 Reconnection Loop
Upon encountering a `WebSocketConnectionClosedException`, `ConnectionError`, or `TimeoutError`:
1.  **Backoff**: Wait for a 2-second grace period to allow the network to stabilize.
2.  **Re-establishment**: Create a new `create_connection` instance.
3.  **State Restoration**: Re-initialize quote/chart sessions and re-subscribe to all active symbols.

### 4.2 Timeouts
- **`ws_timeout`**: Set to **15.0 seconds** (configurable).
- This ensures the `ws.recv()` call does not block indefinitely on "silent" broken connections.
