# Guide: ETF Attribute Reference

## Overview
This document details the validated fundamental and classification attributes available for ETF discovery in the TradingView Scraper. These fields were verified via direct API probing in Jan 2026.

## Validated Attributes

| Attribute ID | Type | Description | Sample Value |
| :--- | :--- | :--- | :--- |
| `category` | ID | Market Category (Asset Class Proxy) | `27` (Lev Equity), `69` (Loans) |
| `aum` | Float | Assets Under Management (Raw Currency) | `713162902765.49` |
| `expense_ratio` | Float | Annual Expense Ratio (%) | `0.0945` |
| `dividend_yield_recent` | Float | Recent Dividend Yield (%) | `1.05` |
| `nav` | Float | Net Asset Value | `691.90` |
| `brand` | String | Fund Family / Brand | `SPDR`, `iShares` |
| `issuer` | String | Issuing Company | `State Street Corp.` |
| `subtype` | String | Instrument Subtype | `etf` |
| `submarket` | String | Market Segment | `otc`, `main` (often empty) |
| `sector` | String | Broad Sector | `Financial` |
| `industry` | String | Specific Industry | `Investment Trusts` |

## Performance Attributes

| Attribute ID | Type | Description |
| :--- | :--- | :--- |
| `Perf.W` | Float | 1-Week Performance (%) |
| `Perf.1M` | Float | 1-Month Performance (%) |
| `Perf.3M` | Float | 3-Month Performance (%) |
| `Perf.6M` | Float | 6-Month Performance (%) |
| `Perf.Y` | Float | 1-Year Performance (%) |
| `Perf.5Y` | Float | 5-Year Performance (%) |
| `Perf.10Y` | Float | 10-Year Performance (%) |
| `Perf.YTD` | Float | Year-to-Date Performance (%) |
| `Perf.All` | Float | All-Time Performance (%) |

## Risk & Session Attributes

| Attribute ID | Type | Description |
| :--- | :--- | :--- |
| `Volatility.D` | Float | Daily Volatility (%) |
| `Volatility.W` | Float | Weekly Volatility (%) |
| `Volatility.M` | Float | Monthly Volatility (%) |
| `change` | Float | Daily Change (%) |
| `change_abs` | Float | Daily Change (Absolute Value) |
| `gap` | Float | Gap from Previous Close (%) |
| `premarket_change` | Float | Premarket Change (%) |

## Example Candidate: SHLD (Global X Defense Tech)

A typical result from the `etf_thematic_momentum` scanner (Jan 2026):

```json
{
  "symbol": "AMEX:SHLD",
  "description": "Global X Defense Tech ETF",
  "close": 71.94,
  "Value.Traded": 33149664.24,
  "Perf.1M": 13.43,
  "ADX": 19.16,
  "aum": 5536142284.51,
  "brand": "Global X",
  "issuer": "Mirae Asset Global Investments Co., Ltd.",
  "expense_ratio": 0.50,
  "category": "27",
  "Perf.Y": 91.97,
  "Perf.YTD": 9.95,
  "Volatility.M": 1.29,
  "change_abs": 0.98
}
```

## Usage Configuration

To utilize these fields in scanner configurations (`configs/scanners/tradfi/*.yaml`), add them to the `columns` list.

```yaml
columns:
  - "name"
  - "close"
  - "volume"
  - "Value.Traded"
  - "aum"
  - "expense_ratio"
  - "dividend_yield_recent"
  - "brand"
  - "issuer"
```

## Recommended Filters

### AUM Filtering
To filter for established funds (> $100M AUM):
```yaml
filters:
  - left: "aum"
    operation: "greater"
    right: 100000000
```

### Yield Filtering
To find high-yield payers (> 3%):
```yaml
filters:
  - left: "dividend_yield_recent"
    operation: "greater"
    right: 3.0
```

### Low Cost Filtering
To find cheap funds (< 0.20% expense):
```yaml
filters:
  - left: "expense_ratio"
    operation: "less"
    right: 0.2
```
