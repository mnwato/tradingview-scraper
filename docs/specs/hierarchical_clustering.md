# Hierarchical Clustering & Risk Bucketing

This specification documents the methodology for grouping correlated assets into hierarchical risk buckets to prevent capital concentration in redundant factors.

## 1. Similarity Metric: robust Correlation

The engine calculates a correlation matrix using the **Intersection of active trading days** to remove the bias caused by disparate market sessions (e.g. 24/7 Crypto vs 5-day TradFi).

$$d_{i,j} = \sqrt{0.5 \times (1 - \rho_{i,j})}$$
- **$\rho_{i,j}$**: Pearson correlation calculated on common non-zero return timestamps.
- **Range**: $[0, 1]$, where $0$ is perfectly correlated and $1$ is perfectly anti-correlated.

## 2. Hierarchical Linkage: Ward's Method

- **Algorithm**: **Ward Linkage**.
- **Rationale**: Switched from Average Linkage to Ward's to minimize intra-cluster variance. This produces tighter, more distinct economic buckets that are easier to interpret.
- **Tree Cutting**:
    - **Method**: `maxclust` (Target Maximum Clusters).
    - **Target**: **25 buckets** for the selected implementation universe.
    - **Adaptive**: The distance threshold automatically tightens ($t=0.3$) during `CRISIS` regimes or loosens ($t=0.5$) during `QUIET` regimes.

## 3. Persistent Clustering

To filter out transient noise, the system uses a **Multi-Lookback Persistence** check:
- Correlations are calculated across **60d, 120d, and 200d** windows.
- Assets are merged into a cluster only if their linkage is statistically stable across at least two of the three windows.

## 4. Metadata Propagation

- **Cluster ID**: Human-readable factor identifier.
- **Primary Sector**: The statistical mode of constituent sectors.
- **Implementation Grid**:
    - **Lead Asset**: Selected via Alpha Ranking for primary execution.
    - **Alternatives**: Redundant venues (e.g. SOL on different exchanges) are preserved for liquidity routing.
- **Fragility Index**: Each cluster is assigned a risk color (🟢/🟡/🔴) based on its average **Expected Shortfall (CVaR)**.
