# Persistence Analysis Specification (v2)

## 1. Objective
Measure the temporal persistence of market regimes (Trend vs. Mean Reversion) for assets in the Raw Pool. This enables filtering candidates based on the stability and expected duration of their behavior.

**Update v2**: Adds Autocorrelation (AC) analysis to validate and characterize the "Memory Depth" of trends and the "Reversion Speed" of oscillations.

## 2. Methodology

### 2.1 Mean Reversion Half-Life ($\lambda$)
For assets with Hurst < 0.5, we model price as an Ornstein-Uhlenbeck (OU) process:
$$ dx_t = \theta (\mu - x_t) dt + \sigma dW_t $$

The Half-Life ($\lambda$) is:
$$ \lambda = \frac{\ln(2)}{\theta} $$

Implementation:
1. Regress $\Delta p_t$ on $p_{t-1}$.
2. $\theta = -\beta$ (coefficient of $p_{t-1}$).
3. Half-life is calculated from $\theta$.

### 2.2 Trend Duration
For assets with Hurst > 0.5, we measure the "Current Trend Age":
- Baseline: EMA-50 of price.
- Duration: Consecutive bars where price is consistently above (Bullish) or below (Bearish) the EMA-50.

### 2.3 Autocorrelation Structure (New)
To distinguish between *structural* regimes and *random* regimes, we analyze the serial correlation structure.

*   **AC Lag-1 ($r_1$)**:
    *   $r_1 > 0.05$: Confirms Momentum (Trend).
    *   $r_1 < -0.05$: Confirms Reversion (Oscillation).
*   **Memory Depth (Trend)**:
    *   Number of consecutive lags ($k$) where $r_k > 0.02$.
    *   Indicates how far back past returns influence future returns.
*   **Reversion Speed (MR)**:
    *   If $r_1 < 0$ and $r_2 > 0$: Oscillatory Mean Reversion (Fast).
    *   If $r_1 < 0$ and $r_2 < 0$: Drifting Mean Reversion (Slow).

### 2.4 Hurst Stability
- Measured over a rolling 120-day window.
- Requirement: 500 days of history for robust stability metrics.

## 3. Data Requirements
- **Lookback**: 500 days (Institutional Production standard).
- **Frequency**: Daily (1d).

## 4. Output Artifacts
- `data/lakehouse/persistence_metrics.json`: Detailed asset metrics including AC structure.
- `artifacts/summaries/latest/persistence_report.md`: Ranking of most persistent assets, with AC validation.
