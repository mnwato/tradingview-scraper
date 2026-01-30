# MT5 Bridge & Custom OMS Design Specification

## 1. Introduction
**Goal**: Enable high-fidelity execution for Forex and CFD instruments where direct API access (e.g., FIX) is cost-prohibitive or unavailable.
The system will bridge the Python-based Quantitative Platform with the MetaTrader 5 (MT5) terminal using a low-latency ZeroMQ messaging layer.

## 2. Architecture

### High-Level Topology
```mermaid
graph LR
    A[Quant Platform (Python)] -- ZMQ REQ/REP --> B[ZeroMQ Server (Python Bridge)]
    B -- TCP Loopback --> C[MT5 Terminal (EA Client)]
    C -- OrderSend --> D[Broker Server]
    D -- OnTrade --> C
    C -- ZMQ PUSH --> A
```

### Components
1.  **Python Client (OMS)**:
    - Generates signals/orders.
    - Manages portfolio state.
    - Sends commands to MT5 via ZMQ.
2.  **ZeroMQ Bridge**:
    - `dwx-zeromq-connector` variant.
    - REQ/REP pattern for synchronous commands (Trade, Data).
    - PUSH/PULL pattern for asynchronous streams (Ticks, Account Updates).
3.  **MT5 Expert Advisor (EA)**:
    - Runs inside MT5 terminal.
    - Listens on ZMQ ports.
    - Translates JSON commands to MQL5 `OrderSend`.
    - Streams ticks and account events back to Python.

## 3. Data Flow

### 3.1 Market Data (Inbound)
- **Ticks**: High-frequency tick data streamed from MT5 `OnTick()` -> ZMQ PUSH -> Python PULL.
- **Bar Data**: Historical requests via ZMQ REQ (Python) -> MT5 `CopyRates` -> ZMQ REP.
- **Account Data**: `OnTradeTransaction` events streamed to keep Python portfolio state in sync.

### 3.2 Order Execution (Outbound)
- **Signal**: Strategy generates a target weight/quantity.
- **Normalization**: Python OMS converts to lots (normalized by contract size and min lot).
- **Transmission**: JSON payload `{action: "OPEN", symbol: "EURUSD", type: "BUY", volume: 0.1, ...}` sent via ZMQ REQ.
- **Confirmation**: MT5 EA returns Ticket ID or Error Code via ZMQ REP.
- **Lifecycle**: Python tracks open orders and maps fills to strategies.

## 4. Risk Management

### 4.1 System-Level Controls
- **Max Drawdown**: Circuit breaker triggers if account equity drops X% from high-water mark.
- **Daily Loss Limit**: Hard stop execution if daily PnL < -Y%.
- **Kill Switch**: Manual or automated "Flatten All" command.

### 4.2 Order-Level Validation
- **Min/Max Lot Size**: Enforce symbol-specific limits before sending.
- **Margin Check**: Pre-trade margin simulation (if data available) or buffer enforcement.
- **Price Band**: Reject orders if drift > Z% from last known tick.

## 5. Protocol Specification
The bridge uses a strict JSON-RPC style protocol over ZeroMQ.

### 5.1 Request (REP Socket)
**Format**: `{"action": "<VERB>", "params": {...}}`

| Action | Params | Response |
| :--- | :--- | :--- |
| `GET_ACCOUNT` | None | `{balance: float, equity: float, margin: float}` |
| `GET_POSITIONS` | None | `{positions: [{ticket, symbol, type, vol, price}, ...]}` |
| `TRADE` | `{type, symbol, volume, price, sl, tp, comment}` | `{ticket: int, error: str}` |
| `CLOSE` | `{ticket, volume}` | `{error: str}` |
| `CLOSE_ALL` | None | `{closed_count: int}` |

### 5.2 Streams (PUSH Socket)
**Format**: `{"type": "<TYPE>", ...payload}`

- **Tick Data**: `{"type": "DATA", "symbol": "EURUSD", "bid": 1.05, "ask": 1.051, "time": 1700000000}`
- **Trade Events**: `{"type": "TRADE", "event": "ORDER_FILL", "ticket": 123, "symbol": "EURUSD", "volume": 0.1, "price": 1.05}`

## 6. Implementation Roadmap
1.  **Prototype**: Establish ZMQ ping-pong between Python and MQL5.
2.  **Data Stream**: Implement tick streaming and history fetching.
3.  **Execution Core**: Implement Market and Limit order types.
4.  **OMS Logic**: Build the Python-side Order Management System state machine.
5.  **Risk Layer**: Implement pre-trade checks and circuit breakers.
