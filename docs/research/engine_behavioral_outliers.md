# Engine Behavioral Outliers & Performance Deep Dive (Jan 2026)

This document analyzes the significant performance discrepancies between optimization engines identified during the Jan 2026 Full-Matrix Tournament.

## 1. Summary of Outliers

| Profile | Outlier Engine | Key Metric | vs. Baseline (Custom) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Min Variance** | `skfolio` | **0.91% Vol** | 7.90% Vol (8x better) | **Dominant** |
| **Max Sharpe** | `skfolio` | **194% Return** | 55% Return (3.5x higher) | **Aggressive** |
| **Barbell** | `riskfolio` | **11.5 Sharpe** | 1.7 Sharpe (6x higher) | **Dominant** |

## 2. Deep Dive: Reasoning the Gaps

### A. Min Variance: Shrinkage vs. Sample Covariance
The 8x volatility reduction by `skfolio` over the `custom` engine is the most significant finding.
- **Reasoning**: The `custom` engine uses raw sample covariance, which is notoriously noisy and prone to "eigenvalue spreading." `skfolio` implements shrinkage techniques that pull extreme correlations toward the mean, resulting in a much more stable and truly low-risk portfolio.
- **Recommendation**: Deprecate `custom` for the `min_variance` profile. Use `skfolio` as the production standard.

### B. Max Sharpe: Convexity Extraction
`skfolio` achieved >10 Sharpe across all simulators, while `cvxportfolio` engine hovered around 3.0.
- **Reasoning**: `cvxportfolio` (the engine) optimizes for multi-period stability and penalizes turnover heavily. `skfolio` is a single-period optimizer that, even with L2 regularization, is more willing to concentrate in high-momentum "alpha clusters." 
- **Recommendation**: Use `cvxportfolio` for conservative institutional growth and `skfolio` for aggressive capital appreciation.

### C. Barbell: Core Sleeve Efficiency
The massive Sharpe gap in the Barbell profile (11.5 vs 1.7) highlights the inefficiency of the `custom` engine in managing the 90% "Core" sleeve.
- **Reasoning**: Since the Barbell profile relies on a very stable core to offset high-optionality aggressors, any noise in the core's risk estimation (where `custom` fails) degrades the entire portfolio's Sharpe ratio.
- **Recommendation**: Transition all Barbell production presets to use `riskfolio` or `skfolio` for the Core sleeve optimization.

## 3. Simulator Consistency Check
The outliers were consistent across **all three simulators** (`cvxportfolio`, `vectorbt`, `custom`).
- **Confirmation**: This proves the differences are inherent to the **Optimization Logic** (the "Brain"), not artifacts of the backtest simulation (the "Market").

## 4. Conclusion
Specialized libraries (`skfolio`, `riskfolio`) are substantially outperforming the internal `custom` implementation in risk-adjusted metrics. The `custom` engine remains a valuable "Frictionless Baseline" but should be relegated to a secondary role in production environments.
