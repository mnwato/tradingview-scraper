# Native MT5 Adapter Design

**Note: Implementation Deferred (Jan 2026)**
The development of this native adapter has been deferred due to the operational overhead of managing Windows-only infrastructure. The codebase contains the full implementation (`tradingview_scraper/execution/mt5/`), but it is not currently active in the production pipeline.

## Overview
This document outlines the architecture for the Native MT5 Adapter, which replaces the legacy ZMQ-based bridge. This adapter utilizes the official `MetaTrader5` Python library to communicate directly with the MT5 terminal.

**Key Constraints:**
- **Windows Only**: The `MetaTrader5` library is only compatible with Windows.
- **Import Guarding**: All MT5-specific imports must be guarded to prevent `ImportError` or crashes on Linux (CI/Production) environments.

## Architecture

The adapter consists of three main components:
1.  **`MT5Client` (Singleton)**: Manages the connection to the MT5 terminal.
2.  **`DataClient`**: Handles market data retrieval.
3.  **`ExecutionClient`**: Handles order execution and account monitoring.

### 1. `MT5Client` Singleton
A thread-safe singleton class responsible for initializing and shutting down the MT5 connection.

**Responsibilities:**
- Initialize `MetaTrader5` with path to terminal (optional) and credentials.
- Maintain connection state.
- Ensure only one initialization occurs.
- Graceful shutdown on application exit.

**Interface:**
```python
class MT5Client:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Singleton logic
        pass

    def initialize(self, **kwargs) -> bool:
        """Initializes the MT5 terminal connection."""
        pass

    def shutdown(self):
        """Shuts down the connection."""
        pass
```

### 2. `DataClient`
Responsible for fetching historical and real-time market data.

**Responsibilities:**
- Poll for current prices (Tick data).
- Fetch historical bars using `copy_rates_range` or `copy_rates_from`.
- Normalize data into internal `Bar` or `Tick` structures.

**Methods:**
- `get_latest_tick(symbol: str) -> Tick`
- `get_history(symbol: str, timeframe, lookback) -> DataFrame`

### 3. `ExecutionClient`
Responsible for sending orders and tracking trade status.

**Responsibilities:**
- Format orders into standard MT5 request dictionaries.
- Submit orders via `order_send`.
- Parse return codes and handle errors (e.g., Requotes, Off-quotes).
- Poll for order/deal updates if necessary (though `order_send` is synchronous).
- Fetch account info (Balance, Equity, Margin).
- Fetch open positions.

**Methods:**
- `submit_order(order: Order) -> OrderResult`
- `get_account_info() -> AccountInfo`
- `get_positions() -> List[Position]`

## Implementation Details

### Import Guarding
To ensure cross-platform compatibility, the `MetaTrader5` library should strictly be imported within a try-except block or conditional check.

```python
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    # Mock mt5 for type checking or dummy behavior if needed
```

Any class that relies on `mt5` must check `MT5_AVAILABLE` during initialization and raise an explicit `EnvironmentError` if running on a non-Windows system where the library is missing (unless in a specific mock/test mode).

### Thread Safety
The `MetaTrader5` library is generally synchronous. If concurrent access is required (e.g., polling data while sending orders), the `MT5Client` should enforce locking mechanisms to prevent race conditions, although the underlying DLL handles some concurrency. A global lock for critical sections is recommended.

## Deployment
- **Environment**: Windows Server / Desktop.
- **Dependency**: `pip install MetaTrader5`
- **Configuration**: `mt5_config.json` (Path to terminal.exe, Login, Password, Server).
