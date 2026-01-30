# Design: Alpha Correlation & Regime Sensitivity (v1)

## 1. Objective
To validate that the replicated technical ratings (`TechnicalRatings`), despite scalar divergence from TradingView's ground truth, maintain a high rank correlation and directional consistency, ensuring they are valid proxies for alpha generation.

## 2. Correlation Protocol

### 2.1 Metrics
For the sample set of assets, calculate:
- **Spearman Rank Correlation**: Measures if the ordering of assets (Best to Worst) is preserved. Target: $\rho > 0.9$.
- **Sign Agreement**: Percentage of assets where `sign(replicated) == sign(ground_truth)`. Target: $> 90\%$.

### 2.2 Regime Sensitivity
Verify that the replicated ratings react correctly to market regimes:
- **Crisis**: Ratings should skew negative (Sell).
- **Expansion**: Ratings should skew positive (Buy).

## 3. Audit Tool Enhancement
Update `scripts/audit/audit_feature_parity.py` to:
1. Fetch ground truth for a larger universe (e.g., 50 assets).
2. Calculate Spearman correlation between `replicated` and `ground_truth` vectors.
3. Report "Rank Fidelity" status.

## 4. TDD Strategy
- **`tests/test_alpha_correlation.py`**:
    - Mock two vectors with high rank correlation but different scales.
    - Verify that the correlation check passes.

## 5. Decision Gate
If Rank Correlation > 0.9, the replicated ratings are **Fit for Purpose** (Alpha Generation), even if absolute scalar parity is not achieved.
