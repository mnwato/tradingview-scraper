# Design Document: Nautilus Parity Integration (v1)

## 1. Objective
Ensure bit-perfect parity between research backtests and live execution by using **NautilusTrader** as the unified event-driven engine. This replaces the legacy `ReturnsSimulator` bypass with a high-fidelity simulation that respects exchange limits.

## 2. Architecture

### 2.1 Metadata Bridge: `NautilusInstrumentProvider`
Nautilus requires strict `Instrument` definitions. This component will:
- Query `data/lakehouse/execution.parquet` (managed by `ExecutionMetadataCatalog`).
- Map unified symbols (e.g., `BINANCE:BTCUSDT`) to Nautilus `InstrumentId`.
- Set `price_precision` and `size_precision` based on `tick_size` and `step_size`.

### 2.2 Data Bridge: `NautilusDataConverter`
- Convert `portfolio_returns.pkl` (daily returns) into Nautilus `Bar` objects.
- Generate a temporary `ParquetDataCatalog` per backtest window.
- Ensure timestamps are aligned with the `market-day` (+4h shift) normalization.
- **Physical Only**: The catalog must strictly contain physical instrument data. No synthetic or inverted return streams are allowed.

### 2.3 Strategy: `NautilusRebalanceStrategy`
This is the core execution logic:
- **Input**: A time-indexed DataFrame of **Net Physical Target Weights** (flattened from Strategy Atoms).
- **On Bar**: 
    1. Calculate `target_qty = (PortfolioValue * TargetWeight) / CurrentPrice`.
    2. **Precision Guard**: Round down to `lot_size` / `step_size`.
    3. **Minimum Gate**: Skip if `target_qty * CurrentPrice < min_notional`.
    4. **Execution**: Submit `MarketOrder` (BUY/SELL based on sign of physical weight).

### 2.4 Backtest Runner: `NautilusSimulator`
- Wraps the Nautilus `BacktestEngine`.
- Maps standard backtest inputs (`returns`, `weights_df`, `initial_holdings`) to Nautilus components.
- **Pre-Flight Check**: Verifies that input weights correspond to valid physical instruments in the Data Catalog.
- Post-run: Extract the NAV curve and trade history to calculate standard metrics (Sharpe, MDD, Turnover).

## 3. Parity Requirements [MET]
- **Friction**: Nautilus transaction costs must be calibrated to match `backtest_slippage` and `backtest_commission`.
- **Divergence Gate**: Annualized return divergence between `cvxportfolio` and `nautilus` must be **< 1.5%**.
- **Observability**: The `NautilusRebalanceStrategy` must log daily NAV snapshots. Silent failures in NAV calculation (resulting in flat 0% return curves) are treated as critical integration bugs.
- **State Integrity**: The `_get_nav()` method must robustly handle `InstrumentId` string conversions between the unified venue format (`AVGO.BACKTEST`) and internal tracking keys.

## 4. Live Bridge (L6)
Once parity is proven in backtest, the same `NautilusRebalanceStrategy` will be deployed to a live `NautilusTrader` node using:
- `BinanceLiveExecutionClient` (Crypto)
- `IbLiveExecutionClient` (IBKR)

## 5. Validation Suite (Phase 168)
A dedicated script `scripts/validate_nautilus_parity.py` validates parity on **Net Physical Weights**:
1.  **Baseline**: `ReturnsSimulator` (Vectorized, Physical Weights).
    - **Configuration**: Must use `rebalance_mode="daily"` and `tolerance=False` to match Nautilus's strict tracking.
2.  **Challenger**: `NautilusSimulator` (Event-Driven, Physical Weights).
    - **Alignment**: Requires "Pre-Start Priming" (feeding T-1 dummy bar) to align T0 execution lag with Vectorized T0 assumption.
3.  **Metrics**: Sharpe and CAGR must match within tolerance (< 1.5% divergence).
4.  **Turnover**: Must match `(Sum(|Delta|) / 2)` standard.

## 6. Audit & Troubleshooting
- **Validation**: Use `scripts/validate_nautilus_parity.py --run-id <ID>` to verify a specific run.
- **Common Failures**:
    - **Flat Returns (0.00%)**: Indicates a failure in `_get_nav()` to retrieve cash or positions. Check logs for "Failed to get cash balance".
    - **High Divergence**: Indicates a mismatch in friction settings (`backtest_slippage`) or timestamp alignment between the vectorized and event-driven engines. Ensure Pre-Start Priming is active in `nautilus_adapter.py`.
