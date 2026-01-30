# Track Report: Optimization Engine Fidelity & Selection Tuning

**Track ID**: `optimization_engine_fidelity_20260101`
**Status**: `COMPLETED`
**Outcome**: **Success** - `CVXPortfolioEngine` fidelity bug fixed; `v3.1` verified as high-alpha option.

## Executive Summary
We successfully diagnosed and fixed a critical implementation flaw in `CVXPortfolioEngine` where "Risk Parity" was being executed as "Mean-Variance Optimization (Risk Aversion=5)". This explained the anomalous high returns/volatility in previous benchmarks.

We also validated the new `v3.1` selection logic (from the V3 Audit track) in a full 4D tournament.

## Key Findings

### 1. Engine Fidelity
*   **Defect**: `CVXPortfolioEngine` fell back to a default `ReturnsForecast - 5*Cov` objective for any profile it didn't explicitly handle (including `risk_parity` and `hrp`).
*   **Fix**: Modified `CVXPortfolioEngine._optimize_cluster_weights` to explicitly delegate `risk_parity` and `hrp` requests to the `CustomClusteredEngine` implementation (super class), which relies on mathematically correct `scipy`/`cvxpy` solvers.
*   **Result**: The engine now respects the risk-based objective.

### 2. Validation Tournament Results (Selection Alpha)
Comparing Equal-Weight returns of Selected Universe vs Raw Universe:

| Mode | Alpha (vs Raw) | Sharpe Delta | Role |
| :--- | :--- | :--- | :--- |
| **v2** | +0.11% | **+1.61** | **Conservative / Stable**. Maximizes risk-adjusted returns by filtering for stability. |
| **v3.1** | **+0.70%** | +1.05 | **Aggressive / Alpha**. Maximizes absolute returns by allowing momentum candidates. |

*Note: `v3.1` effectively replaced the broken `v3`.*

## Recommendations
1.  **Deployment**: Deploy `v3.1` as the default selection mode for "Growth" profiles and `v2` for "Preservation" profiles.
2.  **Engine**: `custom` remains the most reliable engine for complex risk profiles (HRP/RP). `skfolio` is a good secondary. `cvxportfolio` is now safe to use but falls back to `custom` logic for risk profiles anyway.

## Artifacts
*   `tradingview_scraper/portfolio_engines/engines.py`: Patched engine.
*   `artifacts/summaries/latest/selection_alpha_report.md`: Final benchmark.
