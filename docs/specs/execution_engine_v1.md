# Specification: Execution Engine (v1)
**Status**: Proposal
**Date**: 2026-01-06

This document defines the architecture and API contract for the **L6 Execution Layer**, enabling the platform to send audited, validated orders to live and paper venues.

---

## 1. Architecture: The Router-Adapter Pattern

To support diverse venues (Binance, Alpaca, IBKR) while maintaining a unified risk guard, the engine uses a layered approach:

### 1.1 Components
1.  **Lakehouse Reader**: Polls `portfolio_optimized_v3.json` and the drift-monitor's target orders.
2.  **Risk Guard (The Sentinel)**: 
    - Validates order notional against `max_leverage` and `max_asset_exposure`.
    - Verifies `Source_Run` provenance (refuses to execute non-audited orders).
    - Checks `Regime` parity (e.g., if market regime is CRISIS but order is aggressively long, require manual override).
3.  **Execution Router**: Maps `Venue` (e.g., BINANCE) to the correct Adapter.
4.  **Venue Adapters**: Protocol-specific connectors (e.g., `CCXTAdapter`, `IBKRAdapter`).

---

## 2. Adapter API Contract

Every adapter must implement the following base class interface to ensure swapability:

```python
class BaseExecutionAdapter(ABC):
    @abstractmethod
    def get_positions(self) -> pd.DataFrame:
        """Returns current assets, quantity, and notional in base currency."""
        pass

    @abstractmethod
    def submit_order(self, order: OrderRequest) -> OrderResponse:
        """Executes a trade. Must handle precision/lot size via internal metadata."""
        pass

    @abstractmethod
    def get_market_metadata(self, symbols: List[str]) -> Dict[str, MarketLimits]:
        """Fetches Lot Size, Min Notional, and Tick Size from the venue."""
        pass
```

---

## 3. Order Precision & Fidelity

A critical gap in L4/L5 is **Execution Precision**. The Execution Engine must:
1.  **Fetch Live Limits**: Use `CCXT` (load_markets) or IBKR contract details to fetch asset-specific limits.
2.  **Round Down**: Quantities must be rounded down to the nearest `lot_size` to prevent exchange rejection.
3.  **Dust Handling**: If `Size < min_notional`, the order must be skipped and logged as "Below Floor".

---

## 4. Implementation Sequence

1.  **Metadata Integration**: Build `tradingview_scraper/execution/metadata.py` to fetch limits.
2.  **V3 Order Consumer**: Build the `OrderManager` that reads the Multi-Winner manifest.
3.  **Shadow Loop (L5.5)**: A mock adapter that simulates "Perfect Fills" and updates `portfolio_actual_state.json`.
4.  **First Live Adapter**: Implement `BinanceAdapter` using CCXT.

---

## 5. Audit & Compliance

Every live execution must be recorded in the Lakehouse:
- `data/lakehouse/execution_logs.jsonl`: Replay of all fills, latencies, and costs.
- **Audit Ledger**: The fill hash must be recorded in `audit.jsonl` to close the loop from Research -> Live.
