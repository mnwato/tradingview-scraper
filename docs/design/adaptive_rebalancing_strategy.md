# Adaptive Rebalancing Strategy: The 2:1 Golden Ratio

## 1. The Problem of Lag
In high-volatility regimes (Crypto), standard institutional lookbacks (252 days) fail to react to flash crashes or trend reversals.
- **Over-smoothing**: A 252-day covariance matrix dilutes a 3-day crash, delaying the shift to defensive assets (HRP/MinVar).
- **Mismatch**: Optimizing for a 1-year horizon but rebalancing weekly creates a misalignment between the "Predicted Risk" and "Realized Risk".

## 2. The Solution: Balanced Adaptation (2:1)
To capture fast-moving volatility clusters while maintaining mathematical stability, we enforce a **2:1 Ratio** between Training and Testing windows.

$$ R = \frac{T_{train}}{T_{test}} \approx 2.0 $$

### Why 2:1?
- **Responsiveness**: The model "sees" only the recent regime (e.g., the last month).
- **Stability**: The training window is double the holding period, ensuring that the optimization decision is based on *at least* two cycles of the rebalance frequency.
- **Degrees of Freedom**: For a universe of $N \approx 15$ assets, a training window of $T=20$ days ($T > N$) is the mathematical floor for non-singular covariance estimation without excessive shrinkage.

## 3. Configuration Standards

### 3.1 Crypto (Fast-Adaptive)
Optimized for 24/7 Volatility.
- **Train Window**: **20 Days** (Short-term memory).
- **Test Window**: **10 Days** (Bi-weekly rebalance).
- **Ratio**: 2.0.
- **Rationale**: Captures monthly trends; reacts to crashes within 2 weeks.

### 3.2 Institutional TradFi (Stable)
Optimized for Tax Efficiency and Slow Regimes.
- **Train Window**: **126 Days** (6 Months).
- **Test Window**: **63 Days** (Quarterly).
- **Ratio**: 2.0.
- **Rationale**: Filters out weekly noise; captures macro-economic trends.

*(Note: `production_2026_q1` currently uses 252/20 for extreme stability, but the 2:1 principle suggests moving towards 126/63 or 60/30 for dynamic mandates.)*
