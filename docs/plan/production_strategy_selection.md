# Plan: Production Strategy Selection (Q1 2026)

**Status**: Active
**Date**: 2026-01-01
**Goal**: Identify the single best-performing Engine/Profile/Regime combination for live deployment, based on 1-year secular stability and execution fidelity.

## 1. Stage 1: The "Tournament of Winners"
Analyze the secular 17-window results to identify the top 3 candidates.

- **Criteria**:
    - **Primary**: Maximum Aggregate Sharpe Ratio.
    - **Secondary**: Minimum Peak-to-Trough Drawdown (MDD).
    - **Tertiary**: Execution Efficiency (Annualized Turnover < 100%).
- **Action**: Execute a comprehensive tournament across all 5 engines and all 9 profiles (`market` through `adaptive`).

## 2. Stage 2: Execution Fidelity Audit
Verify that the selected candidate performs consistently across all 4 simulators.

- **Fidelity Check**:
    - `Custom` (Frictionless)
    - `CvxPortfolio` (Friction-Aware)
    - `VectorBT` (Vectorized)
    - `NautilusTrader` (Event-Driven)
- **Standard**: Return divergence between `cvxportfolio` and `nautilus` must be < 1.5% annualized.

## 3. Stage 3: Adaptive Calibration
Audit the `adaptive` profile's behavior during the worst-performing windows of the winners.

- **Objective**: Does the Adaptive logic successfully switch to defensive profiles (`hrp`, `risk_parity`) during detected `CRISIS` or `STAGNATION` regimes?
- **Metric**: "Regime Avoidance Alpha" (Return difference between Adaptive and Static MaxSharpe during Crisis).

## 4. Stage 4: Formal Production Manifest
Create the `configs/presets/production_2026_q1.yaml` file pinning the winning parameters.

- **Pinned Params**:
    - `engine`: (e.g., skfolio)
    - `profile`: (e.g., adaptive)
    - `cluster_cap`: 0.25
    - `rebalance_mode`: window
    - `backtest_slippage`: 0.0005

## 5. Execution Sequence
1.  **Tournament Run**: `uv run scripts/backtest_engine.py --tournament --engines all --profiles all`
2.  **Generate Selection Report**: `docs/research/production_candidate_selection.md`
3.  **Approve & Pin**: Final user sign-off on the candidate.
