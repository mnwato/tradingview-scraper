# Design: Multiplicative Probability Scoring (MPS)

## 1. Problem Statement
Current additive scoring ($0.4 \times Mom + 0.3 \times Liq ...$) allows an asset with "Zero Liquidity" but "Infinite Momentum" to be selected. 

## 2. Mathematical Framework: Series System Reliability
In **Reliability Engineering**, the portfolio candidate universe is a **Series System**. For an asset to be "Functional" in a portfolio, it must satisfy ALL criteria (Survival AND Alpha AND Liquidity).

The reliability of a series system $R_s$ is the product of its components:
$$ R_s = \prod_{i=1}^n R_i = R_1 \times R_2 \times ... \times R_n $$

## 3. Component Normalization (The Probabilistic Mapping)
We transform raw metrics $X$ into survival/functionality probabilities $P(X) \in [0, 1]$ using a **Sigmoid-Logistic** or **CDF-Rank** mapping.

1.  **Survival ($P_{health}$)**: $1 / (1 + \exp(-k(PassRate - Threshold)))$.
2.  **Alpha ($P_{alpha}$)**: Percentile Rank in the cross-section.
3.  **Liquidity ($P_{liq}$)**: $1 - \exp(-\text{ADV} / \text{TicketSize})$.

## 4. The Veto Property (Total System Collapse)
If $R_{liq} = 0.0$ (Zero Liquidity), then $R_s = R_{health} \times R_{alpha} \times 0.0 = 0$.
Unlike additive models, a failure in any "Single Point of Failure" (SPOF) component correctly results in system disqualification.

## 5. Implementation Path
- **Utility**: `tradingview_scraper/utils/scoring.py:calculate_mps_score`.
- **Logic**: Use `scipy.stats.percentileofscore` for non-linear normalization.

