from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Protocol, runtime_checkable


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
    stop_price: Optional[float] = None  # Required for STOP
    time_in_force: str = "GTC"
    ref_id: Optional[str] = None


@dataclass
class UnifiedOrderResult:
    id: str  # Order ID / Ticket
    status: str  # "FILLED", "PENDING", "REJECTED", "CANCELED"
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


@runtime_checkable
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
