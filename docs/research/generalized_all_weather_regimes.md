# Generalized All Weather Regime Methodology (Jan 2026)

This document outlines the adaptation of Ray Dalio's "All Weather" portfolio regime matrix for use in multi-asset quantitative systems.

## 1. The Concept

Ray Dalio's original model uses **Growth** and **Inflation** as the two fundamental dimensions that drive asset returns. We adapt these to general statistical proxies that apply equally to Stocks, Bonds, Forex, and Crypto.

| Dalio Dimension | System Proxy | Statistical Definition |
| :--- | :--- | :--- |
| **Growth** | **Growth Axis** | Annualized Mean Return of the portfolio universe. |
| **Inflation** | **Stress Axis** | Weighted combination of Volatility Ratio and DWT Turbulence (Noise). |

## 2. The Four Quadrants

The market is classified into four distinct environments based on these axes:

### Q1: EXPANSION (High Growth / Low Stress)
- **Environment**: Rising prices with low volatility and noise.
- **Classic Assets**: Equities, High-Beta Crypto.
- **Strategy**: Aggressive (Max Sharpe), Momentum.

### Q2: INFLATIONARY TREND (High Growth / High Stress)
- **Environment**: Rising prices but with significant volatility or noise shocks.
- **Classic Assets**: Commodities, Gold, Inversed Volatility.
- **Strategy**: Trend Following with tighter risk stops.

### Q3: STAGNATION (Low Growth / Low Stress)
- **Environment**: Flat or falling prices with very low activity.
- **Classic Assets**: Long-term Bonds, Treasury Bills.
- **Strategy**: Yield Seeking (Min Variance), Cash.

### Q4: CRISIS (Low Growth / High Stress)
- **Environment**: Sharp price declines accompanied by extreme volatility spikes.
- **Classic Assets**: Cash, Hedges.
- **Strategy**: Capital Preservation, Deep Hedging (HRP).

## 3. Implementation Logic

The `MarketRegimeDetector` calculates the **Growth Axis** (annualized return) and **Stress Axis** (vol ratio + spectral noise). 

- **Neutral Points**: 
    - Growth: 5% Annualized Return.
    - Stress: 1.1 (Score units).
- **Refinement**: This 2D approach provides a more granular context than a 1D "Quiet vs Volatile" score, allowing the portfolio engine to select specialized convex solvers based on the specific quadrant.
