# Churn Penalty Audit: HERC vs. Native HRP (Jan 2026)

## 1. Executive Summary
This audit investigates the impact of portfolio turnover on strategy performance, specifically comparing the lower-churn **HERC** baseline with the high-fidelity **Native HRP** implementation.

## 2. Methodology
- **Engines**: `skfolio` (HRP), `custom` (HERC)
- **Windows**: Jan 2025 - Dec 2025
- **Friction Model**: 5 bps slippage, 1 bp commission (Linear)
- **Metric**: Total Implicit Drag = $(Turnover_{HRP} - Turnover_{HERC}) \times \text{Costs}$

## 3. Audit Findings

| Window | HERC Turnover | HRP Turnover | Turnover Delta | Return Delta | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Initial** | 50.0% | 50.0% | 0.0% | +0.37% | **HRP Leads** |
| **Drift** | 0.87% | 4.78% | 3.91% | +0.65% | **HRP Leads** |

- **Implicit Drag**: The total drag from HRP's higher turnover averaged less than **0.01%** per window.
- **Risk Alpha**: Native HRP's return alpha (+0.65%) and superior volatility control (sub-2% vol) massively offset the minor transaction costs.

## 4. Conclusion: "Efficiency" vs. "Precision"
The initial assumption that HRP's churn would erode its alpha was **rejected**.

**Institutional Guidance**:
- **Native HRP** is not "inefficient"; it is **Precise**. The extra rebalancing is purposeful risk-maintenance that preserves capital during periods of asset drift.
- **HERC** remains valuable for highly illiquid assets where any churn is prohibited, but for the standard institutional universe, the "Churn Penalty" of HRP is a negligible price for its superior risk-adjusted profile.
