# Design Doc: Short Risk Isolation & Liquidation Logic

## 1. The Mathematical Asymmetry of Shorting
In quantitative finance, "Risk Isolation" (allocating fixed weights) behaves differently for Long vs. Short positions due to the payoff curve structure.

### 1.1 Long Position (Bounded Loss)
*   **Action**: Buy $100 of Asset A.
*   **Weight**: $w = +0.10$ (10% of portfolio).
*   **Worst Case**: Price $\rightarrow 0$ ($r = -1.0$).
*   **Max Loss**: $100 \times -1.0 = -\$100$.
*   **Impact**: Loss is strictly limited to the allocated capital ($w$). The position "self-liquidates" as it approaches zero.

### 1.2 Short Position (Unbounded Loss)
*   **Action**: Sell $100 of Asset A.
*   **Weight**: $w = -0.10$.
*   **Worst Case**: Price $\rightarrow \infty$ (e.g., $+1500\%$).
*   **Loss**: $100 \times 15.0 = -\$1500$.
*   **Impact**: Loss exceeds allocated capital by 15x. The position grows as it loses money, consuming the entire portfolio.

## 2. The Fallacy of Weight-Based Risk Control
Setting a constraint `MaxWeight = 25%` protects the portfolio **only** for Long positions.
For Short positions, a 25% allocation can mathematically result in a >100% portfolio loss if the underlying asset rises >400% (4x) in a single rebalance period.

$$ \text{Portfolio Return} = \sum (w_i \times r_i) $$
$$ -0.25 \times 4.0 = -1.0 \text{ (Bankruptcy)} $$

## 3. Solution: Isolated Margin Simulation
To align the simulation with realistic risk management (where exchanges liquidate positions before they exceed collateral), we must enforce **Liquidation Caps**.

### 3.1 The Logic
In an **Isolated Margin** account (1x Leverage), a short position is liquidated when the asset price doubles (+100%), consuming the initial collateral.

$$ \text{Realized Return}_i = \begin{cases} 
w_i \times r_i & \text{if } w_i > 0 \text{ (Long)} \\
w_i \times \min(r_i, 1.0) & \text{if } w_i < 0 \text{ (Short) - Capped at 100\% loss}
\end{cases} $$

*Note: With maintenance margin, liquidation happens slightly earlier (e.g., +95%), but +100% is the theoretical limit for 1x short.*

### 3.2 Implementation Strategy
We cannot modify the input `returns_matrix` because positive returns are valid for Longs. We must modify the **Performance Calculation** step in the backtest engine.

1.  **Iterate** through assets.
2.  **Check** weight sign.
3.  **Apply** liquidation cap if Short.
4.  **Sum** contributions.

## 4. Impact on Forensic Audit
This logic explains why the previous forensic audit showed catastrophic losses for `short_all`. The simulation assumed **Cross-Margin** behavior (unlimited liability) on a 157,000% spike.
With **Isolated Margin** logic, the loss on `ADA` (Weight -0.87%) would have been capped at -0.87% of the portfolio, preserving the fund.
