# Track Report: V3 Selection Pipeline Audit & Improvement

**Track ID**: `v3_selection_audit_20260101`
**Status**: `COMPLETED`
**Outcome**: **Success** - `v3.1` outperforms `v3` and `Raw` baseline.

## Executive Summary
The audit of the `v3` selection pipeline revealed a critical flaw: a **"Panic Mode"** triggered by high condition numbers (`kappa > 1e6`) in the correlation matrix. This forced the selector to pick only **1 asset per cluster** in 94% of windows, effectively reducing the strategy to a "Best-of-Cluster" lottery. Additionally, a high "Estimated Cost of Implementation" (ECI) hurdle (2%) was filtering out viable assets.

We implemented `v3.1` with:
1.  **Relaxed Panic Threshold**: `kappa > 1e18` (effectively disabling panic for standard market data).
2.  **Lower ECI Hurdle**: `0.5%` (vs 2.0%), allowing lower-alpha but defensive assets to survive.

## Benchmark Results (Selection Alpha)

| Mode | Alpha (vs Raw EW) | Absolute Return | Sharpe Delta |
| :--- | :--- | :--- | :--- |
| **v2** | +0.11% | 3.92% | **+1.61** |
| **v3** (Old) | -0.31% | 3.49% | +0.42 |
| **v3.1** (New) | **+0.70%** | **4.51%** | +1.05 |

## Key Findings
1.  **Panic Mode was the Killer**: By forcing `top_n=1`, `v3` lost the diversification benefit within clusters. `v3.1` allows the default `top_n=2`, capturing more robust cluster signals.
2.  **ECI Relaxation Added Upside**: Lowering the cost hurdle allowed `v3.1` to capture momentum candidates that were previously deemed "too expensive" relative to their alpha, resulting in the highest absolute return.
3.  **Trade-off**: `v2` (CARS 2.0) remains the **Risk-Adjusted Champion** (Sharpe Delta +1.61), likely due to its heavy weighting of "Stability" (Inverse Volatility). `v3.1` (MPS 3.1) is the **Return Champion**, favoring Momentum and Regime Survival.

## Recommendations
*   **Adopt v3.1** as the standard "Aggressive/Alpha" selection mode.
*   **Retain v2** as the standard "Defensive/Stable" selection mode.
*   **Deprecate v3** (Old).

## Artifacts
*   `scripts/diagnose_v3_internals.py`: Diagnostic tool.
*   `artifacts/summaries/latest/selection_alpha_report.md`: Detailed benchmark.
*   `tradingview_scraper/selection_engines/engines.py`: Contains `SelectionEngineV3_1`.
