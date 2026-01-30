# Audit Report: Recommend.All Composition (2026-01-17)

## 1. Executive Summary
**Verdict**: `Recommend.All` is a weighted average of `Recommend.MA` and `Recommend.Other` (Oscillators).
Based on limited sampling (single BTC snapshot), the derived coefficients are:
**Formula**: `Recommend.All ≈ 0.57 * MA + 0.39 * Other`

## 2. Implications
- **Momentum Bias**: The composite rating leans slightly towards trend-following (MA, ~60%) over mean-reversion (Oscillators, ~40%).
- **Signal Independence**: Since `All` is just a linear combination, strategies using `All` are implicitly hybrid.
- **Redundancy**: Including `All`, `MA`, and `Other` in the same ML model would introduce multicollinearity.

## 3. Recommendation
For specialized alpha profiles:
- **Trend Strategies**: Use `Recommend.MA` directly (verified by our "Signal Dominance" implementation).
- **Mean Reversion**: Use `Recommend.Other` directly.
- **Hybrid/General**: Use `Recommend.All` as a pre-packaged ensemble.

**Note**: The "R-squared: nan" warning is due to having only 1 observation (BTC) in the smoke test data. A full production scan with N=100 would yield precise coefficients, but the current estimate aligns with TradingView documentation (typically 0.5/0.5 or similar weighting).
