# Spec: Barbell Sleeve Diversification & Optimization

## 1. Objective
Refactor the `BARBELL` profile implementation to support independent, mathematically rigorous allocation strategies for each sleeve. Currently, the Aggressor sleeve is restricted to one "Lead Asset" per cluster and is equal-weighted.

## 2. Requirements
- **Core Sleeve**: Should support configurable optimization (default: `risk_parity` or `hrp`).
- **Aggressor Sleeve**: Should support configurable optimization (default: `max_sharpe` or `alpha_weighted`).
- **Intra-Sleeve Diversification**: Allow multiple assets per cluster in both sleeves, while maintaining total cluster caps (e.g., 25% global cluster limit).
- **Sleeve Rebalancing**: Implement a "Master Weights" approach that blends the two optimized sleeves based on the active regime.

## 3. Mathematical Framework
- $W_{total} = w_{agg} \cdot W_{agg}^* + (1 - w_{agg}) \cdot W_{core}^*$
- $W_{agg}^*$: Optimized using high-momentum/high-alpha objective.
- $W_{core}^*$: Optimized using low-correlation/low-volatility objective.
- **Constraint**: Cluster-level weight across both sleeves must not exceed `CLUSTER_CAP`.
