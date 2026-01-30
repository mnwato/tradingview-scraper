# Spec: Calendar-Aware Data Health Audit

## 1. Goal
Ensure that data health checks (gaps, staleness) are aware of exchange calendars. Prevent non-crypto assets (Stocks, Futures, Forex) from being flagged as "Degraded" or "Failed" purely due to weekends or market holidays.

## 2. Institutional Health Standards
### 2.1 Gap Detection
- **Crypto**: 24/7 calendar. Any missing day is a gap.
- **TradFi**: 5/7 calendar (Mon-Fri).
    - Weekends (Sat/Sun) should NOT be counted as gaps.
    - US Market Holidays should NOT be counted as gaps.
- **Tolerance**: Allow up to 5% actual missing data within active trading hours.

### 2.2 Freshness (Staleness)
- **Crypto**: < 24 hours from current timestamp.
- **TradFi**: Adjusted for weekends/holidays. If today is Monday, data from Friday is "Fresh."

## 3. Implementation Logic
- Integrate `exchange_calendars` library for precise market closure detection.
- Map exchange codes (e.g., NYSE, CME, OANDA) to `exchange_calendars` canonical names.
- Update `DataProfile` logic to utilize library-backed calendars for non-crypto assets.
