# Audit: Meta-Portfolio Pipeline Forensic Audit (v1)

## 1. Objective
To review the numerical integrity and forensic accuracy of the multi-sleeve aggregation and flattening process.

## 2. Identified Issues

### 2.1 Numerical Explosion in Aggregation
- **Observation**: `build_meta_returns.py` calculates weighted sums of sub-sleeve returns.
- **Problem**: If sub-sleeves have extreme daily returns (e.g., due to low liquidity or data errors), the meta-returns matrix will inherit these outliers. This can lead to singular covariance matrices in the meta-optimizer.
- **Suggestion**: Implement a `ReturnScalingGuard` that caps daily returns at $|r| \le 1.0$ (100%) for TradFi and $|r| \le 5.0$ (500%) for Crypto during aggregation.

### 2.2 Unbounded Physical Concentration
- **Observation**: `flatten_meta_weights.py` sums weights for the same asset across different sleeves.
- **Problem**: While individual sleeves may have a 25% cap, the combined meta-portfolio could unintentionally concentrate 50% or more into a single asset (e.g., `BTC`) if multiple sleeves select it.
- **Suggestion**: Implement a post-flattening **Concentration Gate** that re-normalizes weights if any physical asset exceeds the global cap (default 25%).

### 2.3 Identity Ambiguity in Meta-Reports
- **Observation**: `generate_meta_report.py` shows "Consolidated Top 10 Assets".
- **Problem**: It doesn't clearly show *which* sleeves contributed to the weight of a physical asset.
- **Suggestion**: Update the "Top Assets" table to include a `Sleeves` column listing the contributing sleeve IDs.

### 2.4 Annualization Scaling
- **Observation**: Meta-performance metrics use standard annualization.
- **Problem**: If the aggregated returns have many gaps (due to inner join), the annualization factor might be misleading.
- **Suggestion**: Report the "Effective Trading Days" used for meta-performance calculation.

## 3. Conclusion
The meta-pipeline is structurally sound but lacks the "Safety Envelopes" required to handle edge cases in multi-sleeve distribution.
