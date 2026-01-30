# Deep Audit: Standardized Max Sharpe (Jan 2026)

**Run ID**: 20260101-025229

**Simulator**: cvxportfolio


## Window 1: 2025-01-06 00:00:00
| Engine         | Return   | Vol    |   Sharpe | Turnover   | Primary Assets                                                     |
|:---------------|:---------|:-------|---------:|:-----------|:-------------------------------------------------------------------|
| skfolio        | 10.62%   | 21.65% |     9.08 | 49.60%     | AMEX:DUST (24.9%), NYSE:ARE (17.1%), OKX:TRUMPUSDT.P (10.9%)       |
| cvxportfolio   | 0.11%    | 2.12%  |     1.02 | 43.02%     | BYBIT:ETHUSD.P (3.2%), AMEX:SPY (3.2%), THINKMARKETS:AUDNZD (3.2%) |
| pyportfolioopt | -1.02%   | 7.11%  |    -2.73 | 48.29%     | NASDAQ:TLT (25.0%), AMEX:SPY (17.8%), NYSE:VICI (17.0%)            |
| riskfolio      | -0.46%   | 4.05%  |    -2.19 | 48.74%     | AMEX:SPY (25.0%), NASDAQ:TLT (21.5%), THINKMARKETS:NZDCAD (12.7%)  |
| custom         | -0.39%   | 3.19%  |    -2.37 | 45.23%     | NASDAQ:TLT (25.0%), OANDA:WHEATUSD (5.8%), BYBIT:CCUSDT (5.2%)     |


## Window 2: 2025-01-29 00:00:00
| Engine         | Return   | Vol    |   Sharpe | Turnover   | Primary Assets                                                     |
|:---------------|:---------|:-------|---------:|:-----------|:-------------------------------------------------------------------|
| skfolio        | 10.42%   | 16.28% |    11.81 | 19.58%     | AMEX:DUST (18.6%), NYSE:ARE (12.8%), NYMEX:HTTG2026 (11.7%)        |
| cvxportfolio   | 0.29%    | 2.43%  |     2.29 | 1.76%      | BYBIT:ETHUSD.P (3.2%), AMEX:SPY (3.2%), THINKMARKETS:AUDNZD (3.2%) |
| pyportfolioopt | -0.20%   | 5.16%  |    -0.72 | 8.58%      | NASDAQ:TLT (25.0%), AMEX:SPY (24.8%), NYSE:VICI (19.7%)            |
| riskfolio      | -0.34%   | 3.36%  |    -1.92 | 12.10%     | AMEX:SPY (25.0%), NASDAQ:TLT (20.5%), THINKMARKETS:EURNZD (12.2%)  |
| custom         | -0.34%   | 6.02%  |    -1.06 | 18.64%     | NASDAQ:TLT (25.0%), NYSE:VICI (25.0%), AMEX:SPY (9.3%)             |


## Overall Performance Summary
| Engine         | Ann. Return   | Ann. Vol   |   Avg Sharpe | Avg Turnover   |
|:---------------|:--------------|:-----------|-------------:|:---------------|
| skfolio        | 194.42%       | 18.89%     |        10.45 | 34.59%         |
| cvxportfolio   | 21.73%        | 6.59%      |         2.98 | 7.59%          |
| pyportfolioopt | 34.59%        | 15.86%     |         2.48 | 22.16%         |
| riskfolio      | 15.14%        | 9.87%      |         2.4  | 20.79%         |
| custom         | 54.67%        | 23.61%     |         2.23 | 26.26%         |