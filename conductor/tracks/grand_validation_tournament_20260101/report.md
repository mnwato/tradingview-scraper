# Track Report: Grand Validation Tournament

**Track ID**: `grand_validation_tournament_20260101`
**Status**: `COMPLETED`
**Outcome**: **Validation Successful**. System is robust across Selection, Engine, and Risk dimensions.

## Executive Summary
A comprehensive 4D tournament (Selection x Engine x Profile x Simulator) confirmed the fidelity of recent fixes and established performance characteristics for the system.

## Key Insights

### 1. Risk Profiles behave as expected
*   **Max Sharpe**: Highest Return (+6.7%), Highest Risk.
*   **Min Variance**: Lowest Risk (MaxDD -2.5%), Lower Return (+3.7%).
*   **Risk Parity**: Balanced (Return +4.7%, Sharpe 3.42).
*   **Benchmark (EW)**: Surprisingly high efficiency (Sharpe 3.64), indicating that **Asset Selection** is the primary driver of Alpha, while Optimization mostly manages risk/exposure.

### 2. Engine Fidelity Confirmed
*   **Risk Parity**: `CVXPortfolio` (Native) and `Custom` (Reference) produced **identical** results (+5.70% Return, 3.51 Sharpe). The "Fake MVO" bug is definitively fixed.
*   **HRP**: `CVXPortfolio` correctly delegates to `Custom` logic, producing identical results.

### 3. Selection Strategy
*   **v3.1 (Alpha)**: Validated as a high-return selector for momentum profiles (+0.70% Alpha vs Raw).
*   **v2 (Stable)**: Remains the most robust all-rounder, performing well even when averaged across defensive optimizers.

## Recommendations
*   **Default Configuration**: Use `Selection=v2`, `Engine=cvxportfolio` (for speed/costs), `Profile=risk_parity` for a balanced production strategy.
*   **Aggressive Configuration**: Use `Selection=v3.1`, `Engine=cvxportfolio`, `Profile=max_sharpe`.

## Artifacts
*   `artifacts/summaries/latest/risk_profile_report.md`: Detailed stats.
*   `artifacts/summaries/latest/selection_alpha_report.md`: Selection stats.
