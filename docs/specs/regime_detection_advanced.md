# Advanced Multi-Factor Regime Detection

The `MarketRegimeDetector` identifies the prevailing market state to dynamically adjust risk allocation (specifically for the Barbell split). It uses a weighted composite score of four statistical pillars to prevent false positives and capture structural shifts.

## 1. Statistical Pillars

### A. Volatility Shock (Weight: 50%)
- **Metric**: Ratio of Short-term (10d) Standard Deviation to Long-term (200d) Standard Deviation.
- **Goal**: Detect sudden panics or regime quietness.

### B. Spectral Turbulence (Weight: 50%)
- **Metric**: **Discrete Wavelet Transform (DWT)** Energy Ratio.
- **Methodology**: Uses Haar wavelets to decompose the global market return series into high-frequency (noise/shock) and low-frequency (secular trend) coefficients.
- **Rationale**: High high-frequency energy signifies market turbulence and instability.

### C. Risk Persistence (Weight: 30%)
- **Metric**: **Volatility Clustering** (Autocorrelation of absolute returns).
- **Goal**: Distinguish between isolated outliers and sustained high-risk regimes. High clustering confirms that "volatility begets volatility."

### D. Structural Complexity (Weight: 20%)
- **Metric**: **Permutation Entropy**.
- **Methodology**: Measures the degree of order in return sequences. 
- **Rationale**: 
    - **Low Entropy**: High degree of order (Strong trending market).
    - **High Entropy**: High degree of randomness (Choppy/Noisy market).

## 2. Regime Classification

The weighted `Regime_Score` is used to classify the market into states:

| Regime | Score Range | Strategy Impact (Barbell) |
| :--- | :--- | :--- |
| **QUIET** | < 0.7 | Increases Aggressors to **15%** (Optionality is cheap). |
| **NORMAL** | 0.7 - 1.8 | Standard **10%** Aggressor allocation. |
| **TURBULENT**| 1.8 - 2.5 | Shrinks Aggressors to **5%** (Focus on high-conviction). |
| **CRISIS** | >= 2.5 | Shrinks Aggressors to **3%** (Survival mode; focus on Core). |

## 3. Resilience Features

- **Neutral Default**: If input data is too short (< 20 days), the system defaults to "NORMAL" to prevent erratic allocation.
- **Cross-Sectional Proxy**: Uses the average returns of the entire universe as a "Global Market Proxy" for detection, ensuring the regime reflects systemic rather than symbol-specific risk.
