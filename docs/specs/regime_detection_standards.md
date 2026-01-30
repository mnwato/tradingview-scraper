# Market Regime Detection Standards (Jan 2026)

This document defines the multi-factor methodology used by the `MarketRegimeDetector` to classify market states.

## 1. Metric Suite

The detector utilizes a combination of spectral, statistical, and Markovian factors:

| Factor | Metric | Rationale |
| :--- | :--- | :--- |
| **Shock** | Volatility Ratio | Measures current 10-day vol vs. historical window vol. Detects sudden regime shifts. |
| **Noise** | DWT Turbulence | Uses Discrete Wavelet Transform (Haar) to measure energy in high-frequency detail coefficients. |
| **Persistence** | Vol Clustering | Autocorrelation of absolute returns. Measures the tendency of volatility to persist. |
| **Memory** | **Hurst Exponent** | R/S Analysis to distinguish between mean-reverting (<0.5) and trending (>0.5) structures. |
| **Stationarity**| **ADF Test** | Augmented Dickey-Fuller test p-value. High values indicate non-stationary/trending price action. |
| **Complexity** | Permutation Entropy | Measure of structural randomness in return sequences. |
| **Hidden State** | **2-State HMM** | Gaussian Hidden Markov Model trained on absolute returns to distinguish between Quiet and Volatile hidden states. |

## 2. Regime Classifications

- **`QUIET`** (Score < 0.7): Low volatility ratio, low turbulence, high stationarity. Aggressor allocation: **15%**.
- **`NORMAL`** (Score 0.7 - 1.8): Standard market conditions. Aggressor allocation: **10%**.
- **`TURBULENT`** (Score 1.8 - 2.5 or HMM Upgraded): High spectral noise (DWT > 0.7) or strong trending behavior (Hurst > 0.65). Aggressor allocation: **8%**.
- **`CRISIS`** (Score > 2.5 or HMM/Quadrant Confirmed): High weighted score (Shock + Noise + Persistence). Aggressor allocation: **5%**.

3. **Quadrant-Based (All Weather) Methodology**

Inspired by Ray Dalio's All Weather model, the system maps the multi-factor metrics onto two fundamental axes to provide a macro-aware context for asset allocation.

| Axis | Proxy | Component Metrics |
| :--- | :--- | :--- |
| **Growth Axis** | **Realized Momentum** | Annualized Mean Return |
| **Stress Axis** | **Inflation/Risk** | Volatility Ratio (35%) + Turbulence (25%) + Persistence (15%) |

### Market Environments (Quadrants):

- **`EXPANSION`** (High Growth / Low Stress): Bullish, low-noise environment. Standard for **Max Sharpe** optimization.
- **`INFLATIONARY_TREND`** (High Growth / High Stress): Bullish but volatile. Requires **Trend Following** with tight risk guards.
- **`STAGNATION`** (Low Growth / Low Stress): Flat, quiet environment. Favors **Yield Seeking** or Cash.
- **`CRISIS`** (Low Growth / High Stress): Bearish, high-stress environment. Mandates **Deep Hedging** or HRP.

## 5. Adaptive Allocation (Jan 2026)

The `AdaptiveMetaEngine` utilizes the quadrant detection to dynamically switch between standardized risk profiles. This ensures that the portfolio's objective is always aligned with the prevailing macro environment.

| Quadrant | Risk Profile | Strategic Objective |
| :--- | :--- | :--- |
| **`EXPANSION`** | `max_sharpe` | Maximize capital growth in stable uptrends. |
| **`INFLATIONARY_TREND`** | `barbell` | Capture volatile alpha while protecting the core. |
| **`STAGNATION`** | `min_variance` | Preserve capital and capture yield in flat markets. |
| **`CRISIS`** | `hrp` | Prioritize structural survival and tail-risk hedging. |
| **`NORMAL`** | `max_sharpe` | Current `AdaptiveMetaEngine` mapping for neutral periods. |

**Audit Fidelity**: Every adaptive switch is recorded in the audit ledger (`audit.jsonl`) with the metadata tags `adaptive_profile` and `market_environment`, ensuring full transparency of the decision chain.

## 6. Bayesian Feedback & HERC 2.0 (Jan 2026)

To move beyond purely historical metrics, the system now incorporates a Bayesian feedback layer:

### A. Black-Litterman Integration
- **Mechanism**: Blends the standardized Ledoit-Wolf covariance with **Regime Views**.
- **View Generation**: High-Hurst (trending) clusters are assigned higher expected returns during `EXPANSION` phases.
- **Benefit**: Achieved a **13% Sharpe improvement** in Max Sharpe tournament runs by refining return forecasts.

### B. HERC 2.0 (Self-Consistent Tree)
- **Standard**: Hierarchical Equal Risk Contribution is now enforced at both the cluster and asset level.
- **Logic**: Replaced alpha-blending with true **Inverse-Volatility** within each hierarchical bucket.
- **Result**: Reduced hierarchical equal-weight (`equal_weight`) volatility by **34%** compared to simple Hierarchical Equal Weighting.
