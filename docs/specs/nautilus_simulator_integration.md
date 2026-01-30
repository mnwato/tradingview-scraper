# Specification: NautilusTrader Simulator Integration (Jan 2026)

This document defines the integration of **NautilusTrader** as a high-fidelity, event-driven backtesting backend for the TradingView Scraper framework.

## 1. Requirements

- **Parity**: NautilusTrader must produce results directionally consistent with `cvxportfolio` for the same weight sequences.
- **Event-Driven Churn**: Unlike vectorized simulators, Nautilus should model the actual execution of discrete orders.
- **Data Fidelity**: Must support daily frequency data converted from our returns matrix.
- **Metrics Integration**: Realized performance (Sharpe, MDD, Turnover) must be mapped to our standardized `calculate_performance_metrics` suite.
- **Physical Flattening**: The simulator must operate strictly on physical symbols (e.g., `BINANCE:BTCUSDT`). All logical abstractions (Strategy Atoms, Synthetic Longs) must be flattened into net physical weights *before* instantiation. The simulator is logic-agnostic.

## 2. Technical Design

### A. Data Layer
- **Component**: `NautilusDataAdapter`
- **Logic**: Convert `pd.DataFrame` returns for **physical symbols** into a list of Nautilus `Bar` objects.
- **Frequency**: Daily.
- **Alignment (Pre-Start Priming)**: A **dummy T-1 bar** must be prepended to the data stream to align Nautilus's execution logic (T-1 Close trade for T0 Return) with Vectorized assumptions (T0 Open trade).

### B. Execution Layer
- **Component**: `NautilusRebalanceStrategy`
- **Logic**: 
    - On initialization: Accept **flattened** `target_weights` (Net Physical Exposure) and `initial_holdings`.
    - **Rebalance**: Weights are matched to timestamp. Initial positions are established on the T-1 Priming Bar to capture full T0 returns.
    - Post-execution: Record trade timestamps and costs.
    - **Constraint**: This component handles *execution* only. It does not perform logic inversion or synthetic mapping.

### C. Simulation Runner
- **Component**: `NautilusTraderSimulator(BaseSimulator)`
- **Workflow**:
    1. Initialize `BacktestEngine`.
    2. Register the `NautilusRebalanceStrategy`.
    3. Run the engine over the 20-day window.
    4. Extract the NAV curve from the `PortfolioAnalyzer`.

## 3. Implementation Status (Jan 2026)

- **Environment**: Successfully integrated into the native `uv` workflow. Requires **Python >=3.11, <3.13** due to `nautilus-trader` binary compatibility.
- **Data Conversion**: Validated `NautilusDataAdapter` logic for converting daily returns into Nautilus `Bar` objects.
- **Simulator Status**: **Production Certified**. The `NautilusTraderSimulator` class is fully operational, validated for parity (~1% divergence) against vectorized engines, and enabled for institutional profiles.

## 4. Q2 2026 Roadmap: Production Parity (COMPLETED)
- **Full Ingestion**: Automated temporary `ParquetDataCatalog` generation per window.
- **Order Execution**: Implemented `NautilusRebalanceStrategy` with `ParityFillModel` for matched friction.
- **Parity**: Validated parity with `scripts/validate_nautilus_parity.py`. NautilusTrader is now the definitive "Production Parity" simulator.
