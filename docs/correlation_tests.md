# Correlation Tests for Portfolio Construction

This note outlines practical correlation checks to support portfolio optimization (min-var, risk parity, barbell) and capital/risk allocation decisions.

## Scope
- Inputs: daily log returns (cleaned/filled) per symbol from `data/lakehouse/portfolio_returns.pkl`.
- Goals: avoid unstable correlations, cap concentration, and detect regimes where correlations spike.

## Data Hygiene
- Use aligned, non-missing windows (drop symbols with < N days or excessive NaNs).
- Winsorize extreme returns (e.g., 1–99% or MAD-based) before correlation.
- Exclude zero-variance columns; verify no all-NaN rows.

## Correlation Computation
- Rolling windows: 20d (fast), 60–90d (medium), 180–252d (slow). Compare stability.
- Estimators: Pearson on log returns; optionally shrinkage (Ledoit–Wolf) to reduce noise.
- Regime flags: track rolling average pairwise correlation and its z-score; high regimes imply reduced diversification.

## Tests / Screens
- Pairwise cap: flag pairs with |corr| > 0.85; consider dropping one or capping combined weight.
- Cluster check: hierarchical clustering on correlation distance (1 − corr); enforce per-cluster weight caps.
- Vol-corr interaction: flag assets with both high vol and high positive corr to current portfolio core.
- Regime alert: if average pairwise corr z-score > 1.5 on 60–90d window, consider tightening gross/net or increasing diversifiers (e.g., gold/defensives).

## Allocation Guidance
- Min-var: drop or heavily cap highly correlated duplicates; prefer lower-vol member of a near-duplicate pair.
- Risk parity: ensure each cluster contributes; apply per-sector/per-asset caps to avoid dominance when corr spikes.
- Hierarchical Risk Parity (HRP): use correlation distance to cluster assets, then allocate via recursive bisection (inverse-variance within clusters, then risk budget across clusters). Helps when covariances are noisy.
- Barbell: keep core low-corr, defensives; confine aggressors to a small sleeve (e.g., 5–10%) and prefer negatively/low-correlated tails where possible.

## Suggested Workflow (script outline)
- Load returns, align dates, drop sparse symbols.
- Compute rolling correlations (20/60/180d) and summary stats: mean, std, max |corr|.
- Produce reports:
  - Top-k highest |corr| pairs per window.
  - Cluster membership and cluster-level weight cap suggestions.
  - Regime flag if average pairwise corr z-score exceeds threshold.
- Feed exclusions/caps into optimizers (e.g., drop pairs > 0.85, cap cluster weights to X%).
- Optional HRP: build a distance matrix (1 − corr), do hierarchical clustering (average/ward linkage recommended to reduce chaining), apply recursive bisection with inverse-variance weights per sub-cluster; optionally cap cluster weights.

## Quick Pseudocode
```python
import pandas as pd
from sklearn.covariance import LedoitWolf
from scipy.cluster.hierarchy import linkage, leaves_list
import numpy as np

rets = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")
rets = rets.dropna(axis=1, thresh=int(0.9 * len(rets)))
rets = rets.dropna()

# Rolling average pairwise corr
avg_corr_60 = rets.rolling(60).corr().groupby(level=0).mean().mean(axis=1)

# Shrunk covariance and correlation
lw = LedoitWolf().fit(rets.values)
shrunk_cov = lw.covariance_
diag = np.sqrt(np.diag(shrunk_cov))
shrunk_corr = pd.DataFrame(
    shrunk_cov / np.outer(diag, diag), index=rets.columns, columns=rets.columns
)

# Top correlated pairs
corr = rets.corr().abs()
pairs = (
    corr.where(~corr.index.to_series().eq(corr.columns.values[:, None]))
        .stack()
        .sort_values(ascending=False)
)
top_pairs = pairs[pairs > 0.85].head(20)

# (Optional) HRP ordering + weights
# Distance matrix for clustering
corr_mat = rets.corr()
dist = np.sqrt(0.5 * (1 - corr_mat))
link = linkage(dist, method="average")  # ward/average are less prone to chaining
order = leaves_list(link)
ordered = rets.columns[order]

# Recursive bisection for HRP weights
weights = pd.Series(1.0, index=ordered)
clusters = [ordered]
while clusters:
    c = clusters.pop(0)
    if len(c) <= 1:
        continue
    mid = len(c) // 2
    left, right = c[:mid], c[mid:]
    for sub in (left, right):
        cov_sub = rets[sub].cov()
        ivp = 1 / np.diag(cov_sub)
        ivp = ivp / ivp.sum()
        weights[sub] *= ivp.sum()  # allocate cluster budget proportionally
    clusters.extend([left, right])
weights = weights / weights.sum()
```

## Operational Notes
- Run before optimization; store a small JSON/CSV report with top pairs, cluster membership/weights, and regime flag.
- If regime flag is high, consider reducing gross exposure, tightening caps, or adding hedges.
- Keep thresholds configurable (e.g., pairwise cap 0.80–0.90, regime z-score 1.5–2.0). Cluster caps can also be applied if one cluster dominates.
- HRP weights can be used as an alternative allocation or as a seed/constraint alongside other optimizers.
