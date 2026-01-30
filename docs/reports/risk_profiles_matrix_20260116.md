# Risk Profiles Matrix Audit (2026-01-16)

## 1. Executive Summary
This audit consolidates the performance metrics for the Q1 2026 Production Certification runs (`binance_spot_rating_*`).

**Key Findings**:
1.  **Short Alpha Dominance**: The `prod_short_all_v2` run produced the highest risk-adjusted returns (Sharpe 1.65), validating the "Rating All Short" strategy as the primary alpha source.
2.  **Long Viability**: The `prod_long_all_v2` run showed strong returns (Sharpe 1.49) but with higher volatility (67% vs 45%) than the short profile.
3.  **MA Profile Weakness**: The Moving Average (MA) profiles significantly underperformed the "All" profiles. `prod_ma_short_v2` failed to generate positive alpha, with most engines defaulting to cash (0% return).

## 2. Risk Profiles Matrix

| Run ID | Strategy | Profile | Best Engine | Sharpe | CAGR | Volatility | MaxDD |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`prod_short_all_v2`** | **Rating All Short** | **MIN_VARIANCE** | **Riskfolio** | **1.65** | **1438%** | **45.0%** | **-6.2%** |
| | | MAX_SHARPE | Custom | 1.63 | 1398% | 50.9% | -7.6% |
| | | EQUAL_WEIGHT | Skfolio | 1.30 | 1455% | 42.5% | -6.0% |
| **`prod_long_all_v2`** | **Rating All Long** | **MAX_SHARPE** | **Custom** | **1.49** | **2272%** | **67.3%** | **-8.7%** |
| | | MIN_VARIANCE | Riskfolio | 1.43 | 1891% | 58.5% | -7.5% |
| | | EQUAL_WEIGHT | Custom | 0.88 | 2482% | 71.2% | -9.5% |
| **`prod_ma_long_v2`** | **Rating MA Long** | **EQUAL_WEIGHT** | **Skfolio** | **0.99** | **1495%** | **41.4%** | **-5.6%** |
| | | MAX_SHARPE | Custom | 0.90 | 1658% | 46.6% | -6.4% |
| | | MIN_VARIANCE | Custom | 0.75 | 1572% | 46.4% | -6.4% |
| **`prod_ma_short_v2`** | **Rating MA Short** | **EQUAL_WEIGHT** | **Skfolio** | **-0.39** | **545%** | **49.5%** | **-8.6%** |
| | | MIN_VARIANCE | Skfolio | 0.00 | 0.00% | 0.0% | 0.0% |
| | | MAX_SHARPE | Skfolio | 0.00 | 0.00% | 0.0% | 0.0% |

## 3. Operational Recommendations
1.  **Deploy `Rating All Short`**: Allocate 60% of risk budget to the `MIN_VARIANCE` profile (Sharpe 1.65).
2.  **Deploy `Rating All Long`**: Allocate 40% of risk budget to the `MAX_SHARPE` profile (Sharpe 1.49) to capture bull runs.
3.  **Deprecate `Rating MA`**: Move both MA profiles back to the research sandbox. The "Rating All" signal is superior.
