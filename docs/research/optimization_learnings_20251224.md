# Optimization Learnings & Model Comparison (2025-12-24)

## 1. Multi-Model Overview

During the latest execution cycle on a 73-symbol mixed universe (Crypto + Trad), we ran three distinct optimization models.

### A. MPT (Modern Portfolio Theory)
- **Minimum Variance**: Favored ultra-low volatility instruments like `THINKMARKETS:CADJPY` and `OANDA:AU200AUD`.
- **Max Sharpe Ratio**: Achieved a backtested Sharpe of **9.01**. Heavy allocation to trending equities (`NYSE:C`, `NYSE:GM`) and precious metals (`AMEX:PSLV`).
- **Observation**: Highly sensitive to recent trend momentum.

### B. Robust Optimization (Downside Focus)
- **Mechanics**: Optimized for **Downside Semi-Variance** while applying a **Liquidity Penalty** (penalizing positions exceeding 1% of average daily volume).
- **Result**: More balanced weights across the universe. Eliminated "lumpy" concentrations seen in MPT.
- **Top Pick**: `NYSE:MRK` and `OKX:BCHUSDT.P` appeared as top liquid candidates.

### C. Antifragile Barbell (Taleb Strategy)
- **Structure**: 90% Safe Core (Max Diversification Ratio) | 10% Convex Aggressors.
- **Core Diversification Ratio**: 5.84.
- **Aggressors**: Concentration in `IPUSDT` and `TONUSDT` due to their high positive skewness and tail-gain potential.

## 2. Market Regime Discovery

- **Correlation Clusters**: High hierarchical linkage between `NYSE:AMT` (Real Estate), `NYSE:DOC` (Healthcare REIT), and `NYSE:CCI` (Cell Towers). These trade as a single "Interest Rate Sensitive" cluster.
- **Regime Shift**: The 20-day average pairwise correlation is showing a significant Z-score increase, indicating a period of market convergence (all assets moving together).

## 3. Data Integrity Insights

- **Commodity/Futures Gaps**: Far-out futures contracts (e.g., `NYMEX:HPJ2026`) have extremely sparse early history. Traditional gap-filling "ghost chases" these symbols.
- **Solution Implementation**: Verified that newest-to-oldest iteration with genesis detection effectively stabilizes the pipeline for these assets.
- **Mixed-Universe Alignment**: The zero-fill strategy for weekend market closures successfully allows 5-day and 7-day assets to coexist in the covariance matrix without dropping rows.

## 4. Actionable Conclusions

1. **Prioritize Robust**: For larger deployments, the Robust model's liquidity guards are essential to prevent market impact.
2. **Aggressor Selection**: `IPUSDT` across various exchanges shows consistent "Antifragility" scores > 1.4, making it the primary candidate for the convex bucket.
3. **Interest Rate Hedge**: The identified REIT/Utility cluster provides a clear target for "Core" diversification in the Barbell model.
