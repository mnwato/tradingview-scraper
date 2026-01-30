# Guide: Researching TradingView Screener Fields and Filters

## 1. Overview
TradingView's Internal Screener API often uses non-intuitive field names and categorical IDs. This guide documents the process for reverse-engineering and discovering the correct fields for new asset classes.

## 2. Discovery Process

### 2.1 Step 1: Baseline Identity
To find the `type` or `category` of an asset class, start by querying a known canonical asset (e.g., SPY for ETFs, BTC for Crypto).

**Tool**: `scripts/debug_screener.py` (Custom debug script)

```python
from tradingview_scraper.symbols.screener import Screener
import json

def debug_identity(symbol_name):
    s = Screener()
    res = s.screen(
        market="america", # or 'crypto', 'forex', etc.
        filters=[{"left": "name", "operation": "equal", "right": symbol_name}],
        columns=["name", "description", "type", "category", "sector", "industry"],
        limit=1
    )
    print(json.dumps(res, indent=2))
```

### 2.2 Step 2: Categorical Audit
Once the `type` is known (e.g., `fund` for US ETFs), perform a categorical audit to find the numeric IDs used for sub-sectors.

```python
def get_unique_categories(market, asset_type):
    s = Screener()
    res = s.screen(
        market=market,
        filters=[{"left": "type", "operation": "equal", "right": asset_type}],
        columns=["name", "description", "category"],
        limit=1000
    )
    categories = {}
    for item in res.get("data", []):
        cat = item.get("category")
        if cat not in categories:
            categories[cat] = item.get("description")
    return categories
```

## 3. Verified Field Mappings (Jan 2026)

### 3.1 US ETF (Market: `america`)
- **Canonical Type**: `fund` (Note: `etf` often returns 0 results in the `america` market).
- **Categories**:
    - `26`, `27`: Equities
    - `61`, `70`, `68`, `59`, `58`, `63`, `62`, `69`, `64`, `56`, `57`: Bonds / Fixed Income
    - `8`, `6`, `4`, `7`, `5`: Commodities

### 3.2 Performance & Technicals
- **Liquidity**: `Value.Traded` (USD volume).
- **Momentum**: `Perf.W`, `Perf.1M`, `Perf.3M`, `Perf.6M`, `Perf.Y`.
- **Trend**: `ADX`, `Recommend.All`.

## 4. Troubleshooting Common Issues

### 4.1 "0 Candidates Found"
- **Check `type`**: Ensure you aren't using a logical type (e.g., `etf`) that differs from the API's physical type (e.g., `fund`).
- **Check `static_mode`**: If using a static list, ensure the `market` parameter in `FuturesUniverseSelector` matches the symbols' exchange (e.g., `america` for `AMEX:`/`NASDAQ:`).
- **Check Field Names**: Some fields use dots (e.g., `Value.Traded`) and are case-sensitive.

### 4.2 "Filtered Out Unexpectedly"
- Review the `L1` hygiene layer. Scanners often inherit a `Value.Traded > 10M` floor. If testing niche assets, check their current daily turnover.
- Use `verbose: true` in the selector to see "After basic filters: X" logs.
