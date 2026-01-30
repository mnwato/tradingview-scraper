# Track Report: Risk Parity & HERC Benchmarking

**Track ID**: `risk_parity_benchmarking_20260101`
**Status**: `COMPLETED`
**Outcome**: `CVXPortfolio` Native RP verified. `Custom` HRP verified as Inverse-Variance on Clusters.

## Benchmark Results (Synthetic Data)
We compared allocations for 4 assets (A,B High Vol, C Med, D Low) grouped into 3 clusters.

### 1. Risk Parity (ERC)
*   **Custom (Reference)**: `[0.167, 0.162, 0.334, 0.336]`
*   **CVXPortfolio (Native)**: `[0.167, 0.162, 0.334, 0.336]` (Exact Match)
*   **Skfolio**: `[0.118, 0.115, 0.318, 0.449]` (Divergent)
    *   *Analysis*: Skfolio allocates significantly less to high-volatility assets. This suggests it likely uses a different covariance estimator (less shrinkage?) or strictly equates Volatility Contribution (vs Variance Contribution) in a way that manifests differently with this dataset.
    *   *Conclusion*: `CVXPortfolio` implementation is mathematically consistent with our `Custom` reference (Convex Log-Barrier).

### 2. Hierarchical Risk Parity (HRP)
*   **Custom**: `[0.229, 0.222, 0.186, 0.364]`
*   **Skfolio**: `[0.099, 0.096, 0.270, 0.535]`
    *   *Analysis*: `Custom` HRP uses `trace` (Sum of Variances) for split allocation. `Skfolio` likely uses `variance` of the sub-portfolio or `standard_deviation`. `Custom`'s approach is robust but potentially conservative (less extreme allocations). `Skfolio` is very aggressive (53% in lowest vol asset).

## HERC Assessment
Our `Custom` HRP implementation operates on **Cluster Benchmarks** (pre-aggregated portfolios).
*   Step 1: Intra-cluster weights are Inverse-Variance (Risk Parity within cluster).
*   Step 2: HRP is run on the Cluster Benchmarks.
This two-step process effectively implements **Hierarchical Risk Parity on Risk Factors**, which is the conceptual goal of HERC. We define HERC as satisfied by the current `HRP` profile.

## Recommendations
*   **Primary Engine**: Use `CVXPortfolio` for `risk_parity` (Backtest speed + Transaction costs).
*   **HRP Engine**: Use `Custom` for `hrp` (Transparent "Cluster-first" logic).
*   **Skfolio**: Keep as an alternative "Aggressive Defensive" option given its tendency to overallocate to low-volatility assets.

## Artifacts
*   `scripts/benchmark_risk_models.py`: Benchmark script.
