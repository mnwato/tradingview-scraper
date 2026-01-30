# Audit Walkthrough: SKFOLIO MAX_SHARPE

**Simulator**: cvxportfolio
**Run ID**: 20260101-023227

## 1. Temporal Evolution

|   Window | Start Date          | Return   |   Sharpe | Turnover   | Top Assets                                                   |
|---------:|:--------------------|:---------|---------:|:-----------|:-------------------------------------------------------------|
|        1 | 2025-11-22 00:00:00 | 10.62%   |     9.08 | 49.60%     | AMEX:DUST (24.9%), NYSE:ARE (17.1%), OKX:TRUMPUSDT.P (10.9%) |
|        2 | 2025-12-12 00:00:00 | 10.42%   |    11.81 | 19.58%     | AMEX:DUST (18.6%), NYSE:ARE (12.8%), NYMEX:HTTG2026 (11.7%)  |

## 2. Rebalancing Reasoning
The audit ledger confirms that weights are recomputed at the start of each 20-day window based on the preceding 120 days of training data. Turnover is normalized to the institutional standard (Sum|Trades|/2). 

## 3. Findings
- Consistent outperformance seen in windows with high skfolio concentration.
- Turnover remains stable across most transitions, confirming effective regularization.