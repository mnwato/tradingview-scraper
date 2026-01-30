# Plan: MT5 Native Integration (Official Lib)

## 1. Context & Pivot
The user has requested to discard the ZMQ-based bridge in favor of the **Official `MetaTrader5` Python Library**.
This moves the integration from a "Remote Socket" model to a "Local IPC" model (Python wrapping the Terminal DLLs directly).

**Critical Constraint**: The `MetaTrader5` library is **Windows Only**.
- **Implication**: The Nautilus Trading Node running this adapter **MUST** execute on a Windows host.
- **Architecture**:
    - **Dev/Backtest**: Can run on Linux (if mocking MT5) or Windows.
    - **Live Execution**: Must run on Windows Server/VPS with MT5 Terminal installed.

## 2. Objective
Build a **NautilusTrader Adapter** (`DataClient` + `ExecutionClient`) that wraps the `MetaTrader5` library. This abstracts MT5 as just another Nautilus venue.

## 3. Implementation Plan

### Phase 4 (Revised): Native MT5 Adapter

#### A. Cleanup (Deprecation)
- [ ] **Remove ZMQ Code**: Delete `tradingview_scraper/execution/mt5/client.py`, `execution.py`, and `mql5/`.
- [ ] **Archive Specs**: Rename `mt5_oms_design.md` to `archive/mt5_oms_design_zmq_deprecated.md`.

#### B. Design & Specification
- [ ] **Create `docs/specs/mt5_native_adapter.md`**:
    - **Architecture**: `MetaTrader5` poll loop -> Nautilus Events.
    - **DataClient**:
        - `subscribe_bars`: Poll `MT5.copy_rates_from`.
        - `subscribe_ticks`: Poll `MT5.copy_ticks_from`.
    - **ExecutionClient**:
        - `submit_order`: Call `MT5.order_send`.
        - `reconciliation`: Poll `MT5.positions_get` vs internal state.

#### C. Implementation (Windows Compatible)
- [ ] **Structure**: Create `tradingview_scraper/adapters/mt5/`.
- [ ] **Config**: Define `MT5DataClientConfig` and `MT5ExecClientConfig`.
- [ ] **Client**: Implement `MT5Client` (Singleton wrapper around `MetaTrader5` functions with thread safety).
- [ ] **Data**: Implement `MT5DataClient` (Nautilus `LiveDataClient`).
- [ ] **Exec**: Implement `MT5ExecutionClient` (Nautilus `LiveExecutionClient`).

### 4. Roadmap Update
- Update `docs/specs/plan.md` to replace "MT5 ZMQ Bridge" with "MT5 Native Adapter".
