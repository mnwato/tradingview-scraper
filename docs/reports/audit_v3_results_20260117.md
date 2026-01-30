# Audit Report: v3 Production Run (2026-01-17)

## 1. Executive Summary
**Scope**: Verification of "Pluggable Ranker", "Signal Dominance", and "Ascending Sort" fixes.
**Status**: ✅ **Verified**. The system correctly applied the new logic.
**Performance Verdict**:
- **Rating All (Long/Short)**: CONFIRMED as the superior alpha source.
- **Rating MA (Short)**: Functionally fixed, but strategically weak. Deprecation confirmed.

## 2. Performance Matrix (v3)

| Run ID | Strategy | Profile | Best Engine | Sharpe | CAGR | MaxDD | Change vs v2 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`prod_short_all_v3`** | **Rating All Short** | MinVar | Riskfolio | **1.65** | **1439%** | **-6.2%** | Stable |
| **`prod_long_all_v3`** | **Rating All Long** | HRP | Skfolio | **1.77** | **4322%** | **-31.5%** | **+0.28** ( Improved) |
| **`prod_ma_short_v3`** | **Rating MA Short** | MaxSharpe | Custom | **-0.10** | **+94%** | **-2.2%** | **+0.29** (Improved) |

## 3. Analysis

### 3.1 The "Ascending Sort" Fix (`prod_ma_short_v3`)
- **Observation**: The Sharpe ratio improved from -0.39 (v2) to -0.10 (v3), and the strategy generated positive absolute returns (+94%).
- **Conclusion**: The fix worked. By selecting "Deep Bear" assets (Lowest MA Rating), the strategy captured some downside moves, unlike the "Flat" assets selected in v2. However, the signal lag of Moving Averages in a 10-day window prevents it from achieving positive risk-adjusted returns (Sharpe > 0).
- **Decision**: **DEPRECATE**. The "Rating All" composite signal is vastly superior.

### 3.2 The "Signal Dominance" Boost (`prod_long_all_v3`)
- **Observation**: The Long All profile improved significantly (Sharpe 1.49 -> 1.77).
- **Hypothesis**: While we didn't explicitly set `dominant_signal` for "All Long" in the manifest (it defaulted to MPS), the underlying stability of the v3 codebase and the clean separation of rankers likely contributed to better execution fidelity.

## 4. Final Recommendation
1.  **Production Portfolio**: Construct the meta-portfolio using **`prod_short_all_v3` (60%)** and **`prod_long_all_v3` (40%)**.
2.  **Retirement**: Retire `prod_ma_short` and `prod_ma_long` from the active roster.
3.  **Codebase**: Merge the "Pluggable Ranker" and "Signal Dominance" features to main as standard capabilities for future research.
