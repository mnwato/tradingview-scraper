# Specification: Unified OMS Interface

## 1. Introduction
This document defines the **Unified Order Management System (OMS)** interface. This abstraction layer decouples the quantitative strategy logic from the specific execution venue (Nautilus/Binance, MT5/Forex, CCXT/Kraken).

## 2. Interface Definition
The interface uses a Python `Protocol` to ensure structural typing compatibility across different adapters.

### 2.1 Core Types
```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"

@dataclass
class UnifiedOrderRequest:
    symbol: str
    side: OrderSide
    quantity: float
    type: OrderType = OrderType.MARKET
    price: Optional[float] = None  # Required for LIMIT
    stop_price: Optional[float] = None # Required for STOP
    time_in_force: str = "GTC"
    ref_id: Optional[str] = None

@dataclass
class UnifiedOrderResult:
    id: str  # Order ID / Ticket
    status: str # "FILLED", "PENDING", "REJECTED", "CANCELED"
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    error: Optional[str] = None

@dataclass
class UnifiedPosition:
    symbol: str
    side: OrderSide
    quantity: float
    avg_price: float
    unrealized_pnl: float
    ticket_id: Optional[str] = None

@dataclass
class UnifiedAccountState:
    balance: float
    equity: float
    used_margin: float = 0.0
    available_margin: float = 0.0
    currency: str = "USD"
```

### 2.2 Protocol
```python
from typing import Protocol

class ExecutionEngine(Protocol):
    """
    Abstract Protocol for Execution Engines (Nautilus & MT5).
    """

    def connect(self) -> None:
        """Establishes connection to the venue or initializes the engine."""
        ...

    def disconnect(self) -> None:
        """Terminates connection and cleans up resources."""
        ...

    def get_account_state(self) -> UnifiedAccountState:
        """Returns the current account financial metrics."""
        ...

    def get_positions(self) -> List[UnifiedPosition]:
        """Returns a list of all currently open positions."""
        ...

    def submit_order(self, order: UnifiedOrderRequest) -> UnifiedOrderResult:
        """
        Submits an order to the execution venue.
        """
        ...

    def close_position(self, symbol: str, quantity: Optional[float] = None) -> UnifiedOrderResult:
        """
        Closes a specific position (fully or partially).
        """
        ...

    def close_all(self) -> List[UnifiedOrderResult]:
        """Emergency flatten: closes all open positions."""
        ...
```

## 3. Implementations

### A. MT5 Adapter (`Mt5OmsAdapter`)
- **Wraps**: `Mt5ExecutionClient` (ZeroMQ).
- **Mapping**: Converts `UnifiedOrderRequest` -> `Mt5Order` -> JSON `TRADE` command.
- **Handling**: Manages ticket-based closure logic internally to expose a netting-like interface.

### B. Nautilus Adapter (`NautilusOmsAdapter`)
- **Wraps**: `NautilusRebalanceStrategy`.
- **Mapping**: Converts `UnifiedOrderRequest` -> `OrderFactory` calls.
- **Context**: Runs *inside* the Nautilus process. It translates the synchronous Unified calls into Nautilus's event-driven/async actions where possible, or queues them. *Note: Nautilus is event-driven, so `submit_order` returns a `PENDING` status immediately.*

### C. CCXT Adapter (`CcxtOmsAdapter`)
- **Future**: Direct REST API wrapping for venues not covered by Nautilus.

## 4. Migration Plan (Phase 4)
Instead of building a bespoke "MT5 Shadow Loop", we will build the **Unified Runner** which accepts an `--engine=[NAUTILUS|MT5]` argument and uses this interface to execute trades.

## 5. Implementation Status (Completed Jan 2026)

### 5.1 Components
| Component | Status | Details |
| :--- | :--- | :--- |
| **Interface** | **Active** | `UnifiedOrderRequest`, `UnifiedOrderResult`, `ExecutionEngine` Protocol defined in `tradingview_scraper/execution/oms.py`. |
| **Nautilus Adapter** | **Active** | `NautilusOmsAdapter` fully implemented wrapping `NautilusRebalanceStrategy`. Verified in Parity Tests. |
| **MT5 Adapter** | **Deferred** | `Mt5OmsAdapter` implemented but deferred due to Windows constraint. |
| **MT5 Bridge** | **Deferred** | Server-side `ZmqServer.mq5` code provided in `docs/specs/mt5_deployment_guide.md`. |
| **Unified Runner** | **Active** | `scripts/run_live_unified.py` replaces legacy shadow scripts. Supports `--engine=NAUTILUS`. |

### 5.2 Next Steps (Phase 5)
- **Deployment**: Install `ZmqServer.mq5` on the physical/cloud Windows execution node (Deferred).
- **Verification**: Run `scripts/run_live_unified.py --mode=SHADOW` to confirm handshake (Deferred).
