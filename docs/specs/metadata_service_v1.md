# Specification: Metadata Service (v1) - Execution Limits

## 1. Objective
Provide venue-specific execution limits (lot_size, min_notional, step_size, fees) to enable precision-aware order generation and ensure parity between backtests and live execution.

## 2. Architecture: Separate Execution Catalog
Unlike the `symbols.parquet` catalog which handles structural and descriptive metadata (SCD Type 2), the execution metadata is stored in a separate, venue-specific catalog to handle the distinct lifecycles of exchange-side limits.

### 2.1 Storage: `data/lakehouse/execution.parquet`
| Column | Type | Source | Description |
|--------|------|--------|-------------|
| symbol | str | Catalog | Unified symbol key (e.g., BINANCE:BTCUSDT) |
| venue | str | Runtime | BINANCE, IBKR, MT5, OANDA |
| lot_size | float | Exchange API | Minimum tradeable quantity |
| min_notional | float | Exchange API | Minimum order value in quote/base |
| step_size | float | Exchange API | Quantity precision step |
| tick_size | float | Exchange API | Price precision step (overrides TV if available) |
| maker_fee | float | Exchange API | Maker fee (decimal, e.g., 0.001) |
| taker_fee | float | Exchange API | Taker fee (decimal) |
| contract_size | float | Exchange API | Multiplier for futures/CFDs |
| updated_at | datetime | System | Last refresh timestamp |

## 3. Implementation: CCXT Enrichment (Migrated from Conductor)
The service uses a hybrid sourcing model. Structural metadata is sourced from TradingView, while execution limits are enriched via exchange-specific connectors.

### 3.1 CCXT Connector Mapping
- `limits.amount.min` -> `lot_size`
- `limits.cost.min` -> `min_notional`
- `precision.amount` -> `step_size`
- `precision.price` -> `tick_size`

## 4. API Contract
```python
# tradingview_scraper/execution/metadata.py

class ExecutionMetadataCatalog:
    def get_limits(self, symbol: str, venue: str) -> ExecutionLimits:
        """Returns rounded limits for order validation."""

    def refresh_from_exchange(self, venue: str, symbols: List[str]):
        """Connects to exchange (CCXT/IBKR) and updates execution.parquet."""
```

## 5. Execution Parity Priority
1. **Nautilus Integration (Crypto/IBKR)**: Use NautilusTrader's `DataCatalog` and `Instrument` definitions as the source of truth for backtest/live parity.
2. **Custom CCXT OMS**: For venues not natively supported by Nautilus or requiring custom routing logic.
3. **MT5 Adapter**: ZeroMQ bridge for Forex/CFD execution (secondary phase).

## 6. Operational Modes & Fallback Policy

The catalog supports two modes of operation to balance research agility with operational safety:

### 6.1 Research Mode (Backtesting)
- **Goal**: Enable simulation even when exchange connectivity is offline.
- **Policy**: If `execution.parquet` lookup fails, fall back to **Institutional Defaults** (defined in `scripts/enrich_candidates_metadata.py`).
- **Usage**: Used by `NautilusSimulator` during discovery and optimization.

### 6.2 Execution Mode (Live Trading)
- **Goal**: Zero rejected orders due to invalid precision/limits.
- **Policy**: **Strict Metadata Required**. If limits are missing or stale (> 24h), the `ExecutionRouter` must raise `MissingMetadataError` and abort the batch.
- **Rationale**: Guessed defaults (e.g., $10 min_notional) can cause rejection loops if the venue requirement is higher (e.g., $500 block trade minimum).
