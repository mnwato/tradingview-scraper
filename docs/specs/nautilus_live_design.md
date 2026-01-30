# Specification: Nautilus Live Execution (L6)

**PRIMARY EXECUTION PATH**: This design supercedes the MT5 Native Adapter for the current roadmap.

## 1. Introduction
This document defines the architecture for deploying the `NautilusTrader` simulator into a **Live Execution Environment**. This enables the platform to trade real capital on Binance (Crypto) and Interactive Brokers (TradFi) using the exact same strategy logic verified in backtesting.

## 2. Requirements
- **Unified Logic**: The `LiveRebalanceStrategy` must inherit from the `NautilusRebalanceStrategy` to ensure 1:1 logic parity.
- **Safety First**:
    - **Shadow Mode**: Ability to stream live data but execute simulated orders ("Paper Trading") to verify signal generation.
    - **Drift Detection**: Real-time alerts if `Fill Price` deviates significantly from `Market Mid`.
    - **Spec Reconciliation**: Validate `ExecutionMetadataCatalog` against live venue specifications (Lot Size, Min Notional) on startup.

## 3. Architecture

### A. Factory & Config
- **Component**: `NautilusLiveEngine` (Factory)
- **Logic**:
    - Accepts `venue` (BINANCE, IBKR) and `mode` (LIVE, SHADOW).
    - Instantiates venue-specific `DataClient` (e.g., `BinanceSpotDataClient`).
    - **LIVE**: Instantiates `ExecutionClient` (e.g., `BinanceSpotExecutionClient`).
    - **SHADOW**: Instantiates `BacktestExecutionClient` (simulating fills locally) but uses `LiveExchange` for data.

### B. Signal Injection
- **Problem**: Backtests use static DataFrames. Live trading requires dynamic updates.
- **Solution**: `FileWatcher` (Internal Polling)
    - The `LiveRebalanceStrategy` implements an internal `_watch_file` thread that monitors the `portfolio_optimized_v3.json` file.
    - When the file modifies, it automatically parses the **V3 Multi-Winner Schema** and triggers a `_rebalance_portfolio` cycle.

### C. Execution Loop
1.  **Startup**: Connect to Venue (or initialize in SHADOW mode).
2.  **Reconcile**: Check `ExecutionMetadataCatalog` vs Venue Instruments. Warning on mismatch.
3.  **Run**: Start Data Streams.
4.  **Signal**: Receive new target weights via file modification.
5.  **Rebalance**:
    - Calculate `Current vs Target`. 
    - **Rounding**: Enforce strict `step_size` and `min_notional` limits from the metadata catalog.
    - **Safety**: Apply a 2% cash buffer to prevent insufficient balance errors.
    - Generate `MarketOrder` list.
    - Submit to Execution Engine.
6.  **Persistence**:
    - After rebalance, invoke `_persist_state()` to sync Nautilus positions to `portfolio_actual_state.json`.

### D. Synthetic State Architecture (Shadow Mode)
- **Problem**: Shadow execution requires valid instruments and account state even when live feeds are unconfigured.
- **Solution**:
    - **Global Position Tracking**: Maintains `_SHADOW_POSITIONS` dictionary to simulate fills without a real exchange account.
    - **Dummy Instruments**: The `_inject_dummy_instruments()` method (invoked during `on_start`) injects `CurrencyPair` objects into the cache.
    - **Synthetic Cash**: The engine registers a dummy `Account` with 100,000 USD balance for SHADOW simulation.
    - **Robust Bar Fallback**: If real-time quotes are missing, the strategy falls back to the most recent daily bar close for pricing.

## 5. Status & Lessons Learned
- **Status**: **Phase 3 COMPLETE (Jan 2026)**
- **Validation**:
    - **Shadow Mode**: Successfully verified signal injection and order generation using `scripts/live/run_nautilus_shadow.py`.
    - **Parity**: Achieved 1:1 logic parity with the Backtest engine (0.0105 divergence in 300d ETF audit).
    - **State Sync**: Verified real-time persistence of shadow positions to the lakehouse.

