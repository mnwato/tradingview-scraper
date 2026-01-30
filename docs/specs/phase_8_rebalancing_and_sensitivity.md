# Phase 8: Systematic Rebalancing & Market Sensitivity

This specification defines the institutional upgrades for the quantitative platform focusing on rebalancing intelligence, market-neutrality auditing, and factor-level visualization.

## 1. Automated Rebalancing Engine (`drift-monitor`)

The system tracks the "Last Implemented State" and compares it to the "Current Optimal Target" to minimize churn while maintaining risk parity.

- **State file**: `data/lakehouse/portfolio_actual_state.json`
- **Partial Rebalancing**: The monitor supports filtering "Dust Trades" via the `feat_partial_rebalance` flag.
    - **Threshold**: Only weight changes $\ge 1\%$ are marked as `EXECUTE` when enabled.
    - **Order Generation**: Generates implementation-ready CSV orders using the `--orders` flag.
- **Operator action**: After implementing new target weights, run `make accept-state` to update the baseline.

### Thresholds
- **Portfolio Turnover Alert**: If $\sum |Target_i - Actual_i| / 2 > 10\%$, trigger `⚠️ REBALANCE`.
- **Urgent Rebalance**: If Turnover $> 20\%$ or any single asset drift $> 7.5\%$.
- **Implementation Status**:
    - `✅ MAINTAIN`: Healthy alignment.
    - `⚠️ REBALANCE`: Strategic drift detected.
    - `🚨 URGENT`: Significant risk breach or factor shift.

## 2. Market Sensitivity & Beta Mapping

Every portfolio profile must be audited for its sensitivity to broad equity market factors.

### Metrics
- **Beta to Benchmark ($\beta$)**: Calculated via regression of profile returns against `AMEX:SPY`.
- **Correlation to Benchmark ($\rho$)**: Measures how much the portfolio's "low variance" is actually just "Market Inverse."
- **Institutional Limit**: If a defensive profile (Min Variance) has $\beta > 0.5$, it is flagged as `⚠️ AGGRESSIVE`.

## 3. Refined Alpha Rank (Execution Intelligence)

The selection of the "Lead Asset" for each cluster is upgraded to include implementation costs.

### Execution Alpha Formula:
$$Alpha_{Execution} = 0.3 \cdot Mom + 0.2 \cdot Stab + 0.2 \cdot Conv + 0.3 \cdot Liquidity$$

- **Liquidity Score**: Composite of `Value.Traded` and **Spread Proxy** ($ATR / Price$).
- **Impact**: Favors high-liquidity, low-spread venues to ensure optimal fill prices.

## 4. Factor Map Visualization

A new high-level visual artifact to represent the distance between hierarchical risk buckets.

### Methodology
- **Cluster Centroids**: Synthetic return series for each of the 25+ clusters.
- **MDS Projection**: Multidimensional Scaling used to project the cluster correlation distance matrix into 2D coordinates.
- **Interpretation**: Clusters grouped close together are "Factor Neighbors" (e.g., Tech and Crypto). Isolated clusters represent unique diversifiers.

## 5. Workflow Integration

The `Makefile` is updated to include:
- `make drift-monitor`: Terminal-based rebalancing dashboard.
- `make factor-map`: Generates `artifacts/summaries/runs/<RUN_ID>/factor_map.png` (promoted to `artifacts/summaries/latest/factor_map.png` after a successful finalize).
- `make audit`: Now includes Beta and Correlation checks.
