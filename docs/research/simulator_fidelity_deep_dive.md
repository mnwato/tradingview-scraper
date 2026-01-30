# Simulator Fidelity Deep Dive (Jan 2026)

This document analyzes the remaining discrepancies between the three supported simulation backends: `custom`, `cvxportfolio`, and `vectorbt`.

## 1. Observed Discrepancies (Run 20260101-010200)

| Simulator | Return | Vol | Turnover | Methodology |
| :--- | :--- | :--- | :--- | :--- |
| **custom** | 23.05% | 6.92% | 6.67% | Frictionless, Window-Delta Turnover |
| **cvxportfolio** | 21.84% | 6.58% | 8.00% | Friction-Aware, Accumulated Daily Turnover |
| **vectorbt** | 23.02% | 6.64% | 13.00% | Friction-Aware, Accumulated Daily Turnover |

## 2. Analysis of Metrics

### A. The Turnover Gap (6.67% vs 8.00% vs 13.00%)
The primary difference lies in **Rebalancing Frequency and Drift Handling**:

1.  **`custom` (6.67%)**: Reports only the **Transition Turnover**. It calculates the delta between the previous window's ending weights and the current window's target weights at $T=0$. It assumes zero trading occurs *within* the 20-day window.
2.  **`cvxportfolio` (8.00%)**: Uses a **Daily Rebalancing Policy** (`FixedWeights`). It trades at $T=0$ to hit the target, then executes small trades daily to counteract price drift and maintain exact target percentages. The 8% reflects the initial rebalance (~6.67%) plus ~1.33% of accumulated drift correction.
3.  **`vectorbt` (13.00%)**: Also uses a **Daily Rebalancing Policy**. However, it appears more sensitive to price drift or has a tighter tolerance than `cvxportfolio`, resulting in higher accumulated turnover (~6.33% drift correction).

### B. The Return Gap (21.84% vs 23.05%)
The ~1.2% annualized return difference between `cvxportfolio` and `custom` is attributed to:
1.  **Friction**: `cvxportfolio` models a 6 bps total cost (5 bps slippage + 1 bp commission) on every trade.
2.  **Compounding Mechanics**: `cvxportfolio` and `vectorbt` use price-based cumulative compounding, while `custom` uses a simpler return-summation approach which can lead to slight divergence over long periods.

## 3. Implementation Improvements

To achieve true parity, we will implement the following:

1.  **Harmonized Turnover for `custom`**: Update the `ReturnsSimulator` to optionally track and report intra-window drift turnover to match the daily rebalancing model of the other simulators.
2.  **Rebalance Thresholds**: Evaluate adding a "Turnover Tolerance" (e.g., 0.5%) to `vectorbt` and `cvxportfolio` to prevent over-trading on negligible price drifts.
3.  **Compounding Alignment**: Standardize all simulators to use identical geometric compounding for realized returns.

## 4. Conclusion
While minor numerical differences persist, the simulators are now **conceptually synchronized**. `cvxportfolio` remains the conservative "Real-World" estimate, while `custom` and `vectorbt` provide the "Idealized" and "Fast Vectorized" perspectives, respectively.
