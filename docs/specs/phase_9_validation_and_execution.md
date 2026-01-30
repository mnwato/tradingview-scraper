# Phase 9 Specification: Backtesting & Execution Intelligence

## 1. Walk-Forward Validation Engine
The platform implements a **Walk-Forward Validator** to bridge the gap between "Estimated Risk" and "Realized Performance".

### Mathematical Framework
For each window $w$:
1.  **Training**: Optimize weights $W_{train}$ on the period $[t - T_{train}, t]$.
2.  **Testing**: Apply $W_{train}$ to the period $[t, t + T_{test}]$.
3.  **Realized Performance**:
    *   **Geometric Compounding**: $R_w = \prod_{i=1}^{T_{test}} (1 + r_i) - 1$
    *   **Realized Volatility**: $\sigma_w = std(r_{port}) \cdot \sqrt{252}$
    *   **Sharpe Ratio**: $Sharpe_w = \frac{\text{Annualized Return}_w}{\sigma_w}$

### Look-Ahead Bias Protection (Dynamic Auditing)
To ensure biological accuracy, the backtest engine performs **dynamic per-window risk auditing** on each training slice. This means:
- No future information from the test window leaks into the training phase.
- Antifragility and tail risk are recomputed on the training window (Skew/TailGain + VaR/CVaR).
- A compatible `Fragility_Score` is derived point-in-time: `Fragility_Score = (1 - Norm(Antifragility_Score)) + Norm(|CVaR_95|)`.
- Asset selection for the "Aggressor" sleeve (Barbell) is based purely on the training-window convexity.
- Asset directions (LONG/SHORT) are re-synchronized from the point-in-time metadata.

### Symbol Alignment & Weight Re-Normalization
Given the mixed universe (24/7 Crypto vs. 5/7 TradFi), the engine handles missing data in test windows as follows:
1. **Weekend Gaps**: TradFi assets yield $0.0$ returns on weekends.
2. **Weight Re-Normalization**: If an asset is present in the training set but missing from the test set (e.g., due to data quality), the remaining assets' weights are re-normalized to sum to $1.0$.
3. **Robust Correlation**: Clustering uses the "Intersection Correlation" method, only calculating relationships on common active trading days.

### Goal Alignment
- **Min Variance**: Goal is $\sigma_{min\_var} < \sigma_{other\_profiles}$.
- **Risk Parity**: Goal is stability of $\sigma_w$ across different regimes.
- **Max Sharpe**: Goal is maximizing $\sum R_w / \sum \sigma_w$.
- **Barbell**: Goal is capturing tail-events (high positive skew) in the "Aggressor" sleeve.

## 2. Cumulative Transition Modeling
To prevent "Friction Amnesia", the engine preserves the realized portfolio value and holdings between walk-forward windows.
- **Window N End $\rightarrow$ Window N+1 Start**: The simulator calculates the cost of closing positions that were removed from the universe and scaling positions to their new target weights.
- **Transaction Cost Identity**: $C_t = \sum |w_{target, t} - w_{realized, t-1}| \cdot (\text{Slippage} + \text{Commission})$

## 3. Capacity & Liquidity Guards
The reporting suite includes a **Capacity Audit** to identify the maximum manageable AUM for each strategy.
- **Slippage Decay Threshold**: If $Return_{Realized} < 0.5 \cdot Return_{Ideal}$, the strategy is flagged as "Capacity Constrained".
- **Asset Bottleneck**: Identifies the single asset with the lowest liquidity in the optimal portfolio and calculates its impact on the total rebalance time.

## 4. Execution Intelligence (Execution Alpha)
...
Selection within clusters now incorporates **Liquidity Risk** to ensure institutional viability.

### Selection Rank ($A$)
$A = 0.3 \cdot Momentum + 0.2 \cdot Stability + 0.2 \cdot Convexity + 0.3 \cdot Liquidity$

Where **Liquidity** is defined as:
$L = 0.7 \cdot \ln(ValueTraded) + 0.3 \cdot \ln(\frac{1}{SpreadProxy})$
$SpreadProxy = \frac{ATR}{Price}$

## 3. Factor Neutrality (Beta Audit)
To ensure profiles aren't implicitly betting on broad market direction without explicit intent:
- **Calculation**: $\beta_{P} = \frac{Cov(R_P, R_{SPY})}{Var(R_{SPY})}$
- **Usage**: Reported for every profile to flag high-beta exposure in supposedly "Defensive" portfolios.

## 4. Self-Healing Data Lifecycle
Updated the `repair_portfolio_gaps.py` logic to handle institutional rate limits:
- **Retry Mechanism**: Exponential backoff on HTTP 429.
- **Multi-Pass**: Verification of alignment integrity after every repair cycle.

## 5. Operational Outputs
- `make backtest` writes per-profile JSON (`artifacts/summaries/runs/<RUN_ID>/backtest_<profile>.json`) and a comparison resume (`artifacts/summaries/runs/<RUN_ID>/backtest_comparison.md`).
- `make finalize` runs backtesting + audit + reporting, publishes the current run to gist, then promotes `artifacts/summaries/latest` to point at that run.
