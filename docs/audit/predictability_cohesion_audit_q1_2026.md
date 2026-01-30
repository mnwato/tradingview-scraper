# Predictability & Cluster Cohesion Audit: Crypto Q1-2026

## 1. Executive Summary
This audit integrates advanced statistical tests (Autocorrelation, Ljung-Box Q-test, and Lead-Lag Cross-Correlation) to verify the internal structure of the crypto candidate universe. We transitioned from a binary "Entropy Veto" to a nuanced "Predictability & Cohesion" framework.

## 2. Self-Predictability Findings (ACF & Ljung-Box)
We analyzed 67 crypto candidates for structural memory. 
- **Statistical Yield**: 37/67 assets (55%) successfully rejected the white-noise null hypothesis (Ljung-Box p < 0.05).
- **Trend Leaders**: 
    - `BINANCE:GIGGLEUSDT.P` (ACF Lag-1: 0.22)
    - `BINANCE:RIVERUSDT.P` (ACF Lag-1: 0.21)
    - `BINANCE:MYXUSDT.P` (ACF Lag-1: 0.21)
- **Insight**: High positive Lag-1 autocorrelation confirms that these assets exhibit strong trend persistence, justifying their inclusion in high-conviction momentum segments.

## 3. Cluster Cohesion & Lead-Lag Audit
Hierarchical Cluster Analysis (Ward Linkage) was audited for factor homogeneity.

| Cluster | Factor Leader | Principal Follower | Lead-Lag Corr (Lag 1) | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Cluster 11 (Gold)** | `OKX:XAUTUSDT.P` | `BINANCE:PAXGUSDT.P`| -0.097 | Synchronous pegs; no clear leader. |
| **Cluster 1 (Large Market)** | `BINANCE:FETUSDT.P` | `BINANCE:CRVUSDT.P` | 0.119 | FET slightly leads the sector rotation. |
| **Cluster 14 (Growth)** | `BYBIT:BROCCOLI.P` | `BINANCE:BROCCOLI714.P` | 0.043 | Minor cross-exchange discovery lag. |

- **Observation**: Most clusters exhibit low lead-lag correlation, suggesting that crypto markets price in information almost instantly across venues (Efficiency Paradox).

## 4. Policy Implementation
- **Section 11 (Selection v3 Spec)**: Formalized the requirement for assets to reject the white-noise hypothesis via Ljung-Box tests.
- **Section 12 (Selection v3 Spec)**: Codified the **Lead-Lag Cluster Verification** standard.
- **Noise Floor**: Confirmed that the 0.999 entropy threshold is sufficient when combined with ACF/Ljung-Box validation.

## 5. Conclusion
The crypto pipeline is now statistically "Hardened." We no longer just trust momentum; we verify the mathematical memory of the trend. This ensures the **Barbell Profile** anchors in assets with verifiable statistical structure.
