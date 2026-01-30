# Specification: Universe Selection 3.0 (Darwinian Selection & MPS)

## 1. Foundational Axioms & Theoretical Grounding

1.  **Ergodicity & The Absorbing Barrier (Darwinian Survival)**: 
    - **Axiom**: Survival is the only prerequisite. 
    - **Evolutionary Analogy**: Selection precedes fitness. An organism that doesn't reach reproductive age has a fitness of zero.
    - **Implementation**: **Survival Veto Gate**. Assets with `P(Survival) < 0.1` are disqualified regardless of alpha.
    
2.  **Multiplicative Risk (Lethal Mutations)**:
    - **Axiom**: High performance cannot compensate for structural failure.
    - **Evolutionary Analogy**: Essential organs are a "Series System." Failure of the heart (Liquidity) cannot be offset by stronger legs (Alpha).
    - **Implementation**: **Log-Multiplicative Probability Scoring (LogMPS)**. Total score is the sum of log-probabilities: $S = \sum \omega_i \ln(P_i)$.

3.  **Information-Theoretic Connectivity (Niche Differentiation)**:
    - **Axiom**: Information overlap is the leading indicator of shared risk.
    - **Evolutionary Analogy**: Species in the same niche (shared risk drivers) compete for the same resources and are vulnerable to the same extinctions.
    - **Implementation**: **Cluster Battles**. Only the fittest asset survives per correlation cluster.

## 2. Requirement: The Darwinian Health Gate (Extinction Testing)
- **Definition**: Assets must prove "Data Integrity" during specific **Stress Events**.
- **Threshold**: `Regime_Survival_Score >= 0.1`.
- **Logic**: Absolute veto if missing history or failed stress test.

## 3. Requirement: Log-Multiplicative Probability Scoring (MPS 3.2)
- **Model**: $S_{total} = \exp(\sum \omega_i \ln(P_i))$
- **Components**:
    - **Momentum** ($P_{mom}$): Trend strength.
    - **Stability** ($P_{stab}$): Inverse volatility.
    - **Liquidity** ($P_{liq}$): Market depth.
    - **Antifragility** ($P_{af}$): Performance under stress.
    - **Predictability** ($P_{entropy}$, $P_{hurst}$): Spectral efficiency.
- **Goal**: Hard-veto of fragile or illiquid assets via near-zero multiplication (log-sum of negative infinity).

## 4. Requirement: Downstream Engine Alignment (The Continuity Gate)

1.  **Numerical Stability (Condition Number Gate)**:
    - **Metric**: **Condition Number ($\kappa$)** of the return covariance matrix.
    - **Constraint**: $\kappa < 10^6$. 
    - **Action**: If $\kappa \ge 10^6$, the system triggers **Aggressive Pruning**, restricting selection to exactly 1 winner per cluster to eliminate redundant highly-correlated assets.

2.  **Transaction Cost Awareness (Estimated Cost of Implementation - ECI)**:
    - **Logic**: Use the **Square-Root Impact Model**: $Cost = \sigma \sqrt{\frac{OrderSize}{ADV}}$.
    - **Constraint**: $Annualized\_Alpha - ECI > 0.02$ (2% net alpha floor).
    - **Veto**: Assets failing this net alpha test are disqualified (e.g., `UNG`, `USO`).

3.  **Metadata Completeness**:
    - **Metric**: **Instrument Definition Parity**.
    - **Requirement**: `tick_size`, `lot_size`, and `price_precision` must be present and valid. 
    - **Veto**: Any symbol lacking execution metadata is disqualified.

## 5. Modular Architecture (Selection Engines)

Selection logic is abstracted into versioned engines:
- **SelectionEngineV3_2 (MPS 3.2)**: High-stability Log-Probability standard (2026 Champion).
- **SelectionEngineV3.1 (MPS 3.1)**: Refined multiplicative standard.
- **SelectionEngineV2.1 (CARS 2.1)**: Champion additive standard (Global Multi-Norm).

## 6. Validation: Cluster Battles & "Liquid Winners"
The selection engine enforces "One Bet Per Factor" via **Cluster Battles**:
- **Mechanism**: Assets are grouped by Hierarchical Clustering (Ward Linkage).
- **Battle**: Assets within a cluster compete based on their LogMPS score.
- **Outcome**: The winner takes all allocation for that factor; losers are cut.
- **Example**: In the Silver Cluster (Run `20260107`), `AMEX:SLV` (Anchor, Score 0.0935) defeated `AMEX:AGQ` (2x Leveraged, Score 0.0264). The Stability component of the LogMPS score penalized the leveraged volatility, correctly prioritizing the core instrument for the selection phase. Leverage is reserved for the downstream Optimizer (Barbell Profile).

## 7. Profile Differentiation (Darwinian vs. Robust)

The V3 engine behavior is modulated by the selected profile:

### 7.1 Stability Gates ($\kappa$)
- **Darwinian Strictness**: Forces aggressive pruning (1 winner per cluster) at $\kappa \ge 10^6$.
- **Robust Strictness**: Extends the limit to $\kappa \ge 10^7$.

### 7.2 Execution Gates (ECI)
- **Darwinian ECI**: Strictly enforces the $Annualized\_Alpha - ECI > 0.02$ net floor.
- **Robust ECI**: Disables the hard ECI gate for experimental validation.

## 8. Audit & Feedback
- **Selection Alpha**: Measured by comparing the "Pruned" universe return vs the "Raw Pool" return.
- **Veto Trace**: Every disqualification is logged with a reason (e.g., "High Friction", "Low Survival") in `selection_audit.json`.

## 9. Spectral Predictability & Asset-Class Baseline
The engine integrates spectral filters to disqualify random-walk noise from the portfolio candidates.

### 9.1 Entropy & Random Walks
- **Metric**: **Permutation Entropy ($P_{entropy}$)** and **Hurst Exponent ($P_{hurst}$)**.
- **Principle**: We distinguish between "Informative Trends" and "Statistical Artifacts".
- **Baseline Drift**:
    - **TradFi Equities**: Typically score 0.85–0.95 entropy. Baseline threshold set at **0.97**.
    - **Crypto Assets**: Exhibit significantly higher microstructure noise (unpredictability). Baseline threshold relaxed to **0.999** for crypto-centric sleeves to delegate alpha-filtering to the risk engines.
- **Random Walk Zone**: Assets with Hurst values in the **0.48–0.52** range are flagged as random walks and vetoed.
- **Tracking Quality (Fidelity Gate)**: Assets pegged to underlying commodities (e.g. Gold) must maintain a correlation > 0.90 with the underlying (e.g. `XAUUSDT.P`). Failure to track results in immediate veto (e.g. `BINANCE:PAXGUSDT.P` disqualification).

### 10. Portfolio Engine Delegation (The "Noise Floor" Philosophy)
As of 2026-01-08, the role of Natural Selection has shifted from a restrictive "Alpha Filter" to a permissive **"Noise Floor"**.

### 10.1 Rationale
Empirical benchmarking (Phase 33) demonstrates that strict selection (Top 5-10) often suffers from concentration risk and "Late Entry Drift." Expanding the selection universe to **Top 25-50** allows downstream **Portfolio Engines** (Barbell, HRP) to:
1.  **Differentiate Risks**: Use full-rank covariance matrices to identify nuanced factor groups.
2.  **Optimize Weights**: Penalize high-volatility/low-signal assets via weighting rather than binary exclusion.
3.  **Improve Stability**: Achieve higher Sharpe ratios and lower drawdowns by exploiting a broader diversification base.

### 10.2 Guidelines
- **Thresholds**: Selection `threshold` should be kept low (0.0–0.1) or disabled for volatile asset classes like crypto.
- **Top N**: For production sleeves, `top_n` should be set to at least **25 candidates** to ensure the risk engines have sufficient statistical degrees of freedom.
- **Spectral Vetoes**: Maintain strict entropy (0.995) and Hurst (0.48-0.52) gates to ensure that while the universe is broad, it is free of mathematically broken random walks.

## 11. Statistical Predictability (ACF & Ljung-Box)
To further refine the "Noise Floor," we analyze the internal memory of return series.

### 11.1 Self-Predictability Metrics
1.  **Autocorrelation (ACF Lag-1)**: Measures the correlation of an asset with its own immediate past. 
    - **Positive ACF**: Indicates trend persistence (momentum follows momentum).
    - **Negative ACF**: Indicates mean-reversion (overextended moves tend to snap back).
2.  **Ljung-Box Q-Test**: A statistical test for the "White Noise" null hypothesis.
    - **Standard**: Assets must achieve a p-value < 0.05 to reject the white-noise hypothesis and be considered "Self-Predictable."

## 13. Selection Ranking & Signal Dominance (v3.6.4)

### 13.1 Pluggable Ranking Interface
The selection engine now supports a configurable ranking interface, allowing profiles to define *how* assets are sorted and *which* signals drive the alpha score.

#### Ranking Schema
```json
"selection": {
  "ranking": {
    "method": "alpha_score",  // Sorting metric (default: alpha_score)
    "direction": "descending" // Sort order: descending (Bullish) or ascending (Bearish)
  }
}
```

### 13.2 Signal Dominance (MPS Overrides)
To prevent generic factors (like Momentum) from overshadowing specific strategy signals (like Rating MA), profiles can assert **Signal Dominance** via the `features` block.

#### Configuration
```json
"features": {
  "dominant_signal": "recommend_ma",  // The primary alpha driver
  "dominant_signal_weight": 3.0       // Boost weight (Default: 3.0)
}
```
**Behavior**:
1.  **Boost**: The dominant signal's weight is set to 3.0 (vs default ~1.0).
2.  **Dampen**: If the dominant signal is *not* `momentum`, the generic `momentum` weight is automatically dampened to 0.5 (from 1.75) to prevent signal drift.

### 13.3 Profile Examples
- **Rating MA Short**:
    - `ranking.direction`: "ascending" (Select Lowest Score = Strongest Bear)
    - `features.dominant_signal`: "recommend_ma" (Prioritize MA Rating over generic Momentum)
- **Rating All Long**:
    - `ranking.direction`: "descending" (Select Highest Score = Strongest Bull)
    - `features.dominant_signal`: "recommend_all" (Prioritize Composite Rating)
