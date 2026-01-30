# Audit Plan: Meta-Portfolio Validation Run (2026-01-17)

## 1. Objective
Perform a definitive validation run of the `meta_super_benchmark` meta-portfolio, aggregating the now-repaired v3 production sleeves. The goal is to certify that the "Meta-Layer" correctly diversifies across strategy logic (All vs MA) and direction (Long vs Short).

## 2. Target Profile
- **Profile**: `meta_super_benchmark`
- **Sleeves**:
    1.  `long_all` (`prod_long_all_v3`) - Rating All Long
    2.  `short_all` (`prod_short_all_v3`) - Rating All Short
    3.  `long_ma` (`prod_ma_long_v3`) - Rating MA Long
    4.  `short_ma` (`prod_ma_short_v3`) - Rating MA Short

## 3. Execution Steps

### 3.1 Verify Inputs
Ensure all 4 sleeves have generated valid return streams (`.pkl` files) for the target risk profiles (`hrp`, `min_variance`, `barbell`).
*Note: We previously fixed HRP generation for `long_ma`.*

### 3.2 Execute Meta-Pipeline
Run the meta-production flow to:
1.  **Construct Meta-Returns**: Join sleeve returns into a unified matrix.
2.  **Optimize Meta-Allocation**: Allocate capital to sleeves using `hrp`, `min_variance`, etc.
3.  **Flatten Weights**: Map meta-weights back to physical assets.
4.  **Simulate**: (Optional/Implicit via Flattening) - We verify the *allocation logic*.

### 3.3 Audit Metrics
Analyze `artifacts/summaries/latest/meta_portfolio_report.md` to compare:
- **Meta-HRP** vs **Meta-EqualWeight**: Does risk parity provide better stability?
- **Correlation Matrix**: Are Long and Short sleeves truly uncorrelated?

## 4. Deliverables
- Validated `meta_portfolio_report.md`.
- `portfolio_optimized_meta_hrp.json` (Final Target Weights).
