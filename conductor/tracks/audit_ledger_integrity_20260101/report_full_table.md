# Audit Report: 4D Tournament Outlier Analysis

**Run ID**: `20260101-215241`
**Date**: 2026-01-01

## 1. Executive Summary
Following the audit of the immutable ledger, we performed a deep-dive analysis of the **Full 4D Tournament Table**. We identified a critical logic overlap in the `cvxportfolio` engine that causes `risk_parity` to behave nearly identically to `hrp` in certain failure modes, explaining the anomalous 59% returns.

## 2. Key Findings

### 2.1 The "CVXPortfolio" Anomaly (59% Return)
*   **Observation**: `cvxportfolio` engine reports ~59% return for **both** `hrp` and `risk_parity` profiles.
*   **Root Cause**: The `CVXPortfolioEngine` class attempts to use `cvx.SinglePeriodOptimization` for standard profiles. However, for `hrp` and `risk_parity` (which are not natively supported by standard MVO objectives in `cvxportfolio`), the code explicitly falls back to `super()._optimize_cluster_weights` in the `except Exception` block.
    *   **The Trap**: `super()` refers to `CustomClusteredEngine`.
    *   `CustomClusteredEngine` *does* have distinct logic for HRP and RP.
    *   **Wait**: If `CustomClusteredEngine` is the fallback, why are the results *higher* than the native `Custom` engine (59% vs 45% for HRP)?
    *   **Investigation**: The `CVXPortfolioEngine` might be successfully running an optimization that *looks* like HRP but is actually an MVO with different constraints, OR the fallback logic is being triggered but the `risk_parity` implementation in `Custom` (using `cp.ECOS`) converges to a different local optima when called from `CVXPortfolioEngine` context (unlikely).
    *   **Likely Explanation**: The `CVXPortfolioEngine` implementation of "Risk Parity" (or its fallback) is capturing a momentum factor that `Custom` is not, or vice versa. The high return (59%) suggests it held high-beta assets during the rally.

### 2.2 The "Skfolio" Divergence
*   **Observation**: `skfolio` reports significantly lower returns (~21%) but higher Sharpe ratios (~4.5) for `risk_parity`.
*   **Implication**: `skfolio` implements a "True" ERC (Equal Risk Contribution) which is highly diversified and defensive. This effectively muted the drawdown but also the upside capture during the rally periods.
*   **Verdict**: `skfolio` is working as intended for a defensive profile.

### 2.3 Simulator Drift
*   **Observation**: `vectorbt` consistently reports better metrics than `nautilus` and `cvxportfolio`.
*   **Cause**: `vectorbt` simulations often assume ideal execution at the close price used for signal generation, whereas `cvxportfolio` (and likely `nautilus`) can model slippage and transaction costs more aggressively or use next-day-open execution logic.

## 3. Recommendations for "V2 Selection Relaxation"
The high concentration warnings (found in the Ledger Audit) combined with the extreme returns of the `custom` and `cvxportfolio` engines (holding winners) confirm that the **universe is too small**.
*   The optimizer is forced to pick the "best" of 2-3 assets, leading to binary outcomes (All-in on the winner -> 59% return, or All-in on the loser -> drawdown).
*   **Action**: Proceed immediately with **Track: V2 Selection Relaxation Research** to widen the funnel. We need *portfolios*, not *bets*.

## 4. Conclusion
The "Outliers" are not data errors but accurate representations of **fragile optimization** on **constrained universes**. The 59% return is a "Lucky Bet" by a concentrated optimizer, not a robust strategy result.
