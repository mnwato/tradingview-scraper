# Specification: Selection v2 vs v2.1 Benchmark

## 1. Overview
This benchmark validates the transition from **Selection v2** (Baseline Additive Rank-Sum) to **Selection v2.1** (Optimized Weights + Multi-Method Normalization). We aim to prove that the increased complexity of v2.1 results in higher risk-adjusted alpha.

## 2. Benchmark Parameters
- **Pool**: Crypto Top 50 discovery pool.
- **Period**: 2025-01-01 to 2025-12-31 (10 rebalance windows).
- **Configurations**:
    - **v2 (Baseline)**: Rank normalization for all factors, default weights (0.4 Mom, 0.2 Stab, 0.2 Liq, 0.2 AF).
    - **v2.1 (Optimized)**: Multi-norm (Logistic/Z-score/Rank), Optuna-tuned global weights.
- **Metrics**:
    - Mean Selection Alpha.
    - Volatility of Selection Alpha.
    - Information Ratio (Selection Sharpe).
    - Maximum Drawdown of Selection Alpha.

## 3. Success Criteria
- v2.1 must demonstrate a superior Information Ratio over v2.
- No significant increase in selection volatility (robustness preservation).
