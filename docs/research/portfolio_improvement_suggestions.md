# Suggestions for Portfolio Improvement
**Date**: 2025-12-21

## 1. Algorithmic Refinements

### A. Downside Semi-Variance (Handling Fat Tails)
- **Current**: Optimizer uses standard standard deviation (Covariance).
- **Suggestion**: Use **Semi-Variance** (only penalizing downward moves). This is critical for crypto, where upward volatility is beneficial, and downward volatility often has "fat tails" (extreme outliers).

### B. Hierarchical Risk Parity (HRP)
- **Current**: standard Risk Parity.
- **Suggestion**: Implement **HRP**, which uses tree-clustering to group correlated assets (e.g., all BTC-linked perps) before allocating. This prevents "Cluster Crowding" where the optimizer over-allocates to similar assets.

## 2. Structural Improvements

### C. Transaction Cost & Slippage Model
- **Current**: Zero cost assumption.
- **Suggestion**: Integrate a **Liquidity Penalty**. Symbols with lower `Value.Traded` should receive a weight haircut to account for the impact of rebalancing large positions.

### D. Multi-Timeframe (MTF) Alpha Weights
- **Current**: Binary signal (Long/Short).
- **Suggestion**: Weight the initial "Alpha" contribution based on the strength of the trend (e.g., ADX > 40 gets higher conviction than ADX > 20).

## 3. Data Integrity

### E. Look-back Window Sensitivity
- **Current**: 180-day fixed window.
- **Suggestion**: Implement **Walk-Forward Optimization**. Volatility regimes in crypto shift rapidly; using a shorter decay factor (e.g., Exponential Weighted Moving Average) for the covariance matrix would capture regime shifts (like the current short bias) more accurately.
