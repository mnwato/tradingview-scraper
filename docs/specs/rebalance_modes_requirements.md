# Requirements: Backtest Rebalance Modes

## 1. Overview
The quantitative platform must support consistent rebalancing logic across all high-fidelity and research-grade simulation backends. This ensures that strategy performance is comparable regardless of whether a vectorized or event-driven simulator is used.

## 2. Core Requirements

### R1: Standardized Rebalance Frequency
The system must support two primary rebalance modes:
- **Window-based (`window`)**: Rebalance once at the start of each walk-forward test window. This is the **default** production mode.
- **Daily-based (`daily`)**: Rebalance at every trading day within the test window to maintain constant target weights.

### R2: Feature Flag for Drift Tolerance
In `window` mode, the system should optionally support intra-window rebalancing if asset weights drift significantly from their targets.
- **`feat_rebalance_tolerance`**: A boolean flag to enable/disable drift-based checks.
- **`rebalance_drift_limit`**: A float defining the threshold (e.g., 0.05 for 5%) that triggers an emergency rebalance within a window.

### R3: Consistent Default Behavior
- The default rebalance mode across the entire platform must be `window`.
- All simulators must honor the `feat_rebalance_mode` manifest setting.

### R4: Friction Parity
- Friction (slippage and commissions) must be applied consistently in both modes.
- In `window` mode, friction is primarily incurred at the start of the window.
- In `daily` mode, friction is incurred whenever a drift-correction trade is made.

## 3. Scope
This requirement applies to the following simulators:
- `cvxportfolio`
- `vectorbt`
- `nautilus` (currently using `ReturnsSimulator` placeholder)
- `custom` (`ReturnsSimulator`)
