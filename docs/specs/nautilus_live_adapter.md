# Specification: Nautilus Live Adapter (Binance/Alpaca)

## Overview
The Nautilus Live Adapter bridges the validated research pipeline to real-world execution venues. It utilizes the `NautilusTrader` framework to handle high-frequency event processing, order management, and connectivity.

## Objectives
- **Venue Connectivity**: Support Binance (Crypto) and Alpaca (TradFi) as primary execution hubs.
- **Execution Fidelity**: Strictly enforce lot sizes, min notionals, and tick sizes fetched from the Metadata Service.
- **State Persistence**: Sync Nautilus portfolio state back to the lakehouse `portfolio_actual_state.json`.
- **Safety Gates**:
    - **Max Position Cap**: Prevent single asset exposure > manifest limit.
    - **Rebalance Drift Gate**: Only execute if drift exceeds the `feat_rebalance_tolerance`.
    - **Kill-Switch**: Manual emergency halt capability.

## Architecture
1.  **NautilusExecutionEngine**: The core orchestrator that loads the `ExecutionMetadataCatalog`.
2.  **LiveStrategy**: A specialized Nautilus Strategy that:
    - Subscribes to 1m or 1d bars for current holdings.
    - Receives target weights from the latest optimized run.
    - Calculates required orders (Target Weight -> Units).
    - Submits orders via the `LiveAdapter`.
3.  **Audit Ledger**: Every live trade must be cryptographically signed and logged in `audit.jsonl`.

## Implementation Phases
- [x] **Phase 1**: Read-only Paper Trading Adapter (Binance Testnet). (Completed)
- [ ] **Phase 2**: Order Submission with strict lot/notional rounding.
- [ ] **Phase 3**: Persistence loop (Nautilus -> Lakehouse).
- [ ] **Phase 4**: Production deployment (Hard-Sleeved).

## Next Task
- [ ] Implement `Phase 2`: Order Submission logic in `LiveRebalanceStrategy`.
