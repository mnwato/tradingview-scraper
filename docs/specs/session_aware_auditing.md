# Specification: Session-Aware Data Auditing & Institutional Recovery

## Overview
This specification addresses the systematic misclassification of valid market data as "gaps" in the quantitative portfolio pipeline. These false positives primarily affect Forex and international Futures (e.g., EUREX), leading to the unnecessary exclusion of global diversifiers from the candidate universe.

## Problem Statement
The current data auditing logic assumes a standard UTC midnight-to-midnight daily bar. However, institutional markets operate on session-based calendars that do not align with UTC days:
1.  **Session Shift**: Forex and many Futures open on Sunday evening (21:00/22:00 UTC). TradingView timestamps the "Monday" session bar using this Sunday timestamp.
2.  **Holiday Mismatch**: Non-US exchanges (e.g., EUREX) have different holiday schedules (Boxing Day, Whit Monday). Falling back to the NYSE calendar results in false gaps on European holidays.
3.  **Missing Calendar Mapping**: The `FX` calendar specified in metadata is invalid in the `exchange_calendars` library, forcing a fallback to the incorrect NYSE (`XNYS`) calendar.

## Requirements

### 1. Market-Day Normalization
- The system must identify bars by their **Market Closing Date** rather than their literal UTC date.
- **Rule**: If a timestamp is between 20:00 and 23:59 UTC, it should be normalized to the **next day** for the purpose of calendar session validation.
- This applies to `FOREX` and `FUTURES` data profiles.

### 2. Institutional Calendar Mapping
- **EUREX**: Must be mapped to the Frankfurt (`XFRA`) calendar.
- **Forex Brokers** (THINKMARKETS, OANDA, FX_IDC): Must be mapped to a valid 24/5 calendar (e.g., `XCME` or a robust global proxy).
- **ICE**: Must be mapped to `ICEUS`.

### 3. Data Integrity Logic (`detect_gaps`)
- The `LakehouseStorage.detect_gaps` method must use Market-Day normalization before calling `cal.sessions_in_range`.
- Weekends and legitimate institutional holidays must be excluded from gap counts.

## Implementation Design

### Metadata Update
- Modify `DEFAULT_EXCHANGE_METADATA` in `metadata.py` to include canonical calendar names.

### Normalization Layer
- Introduce a helper function `to_market_date(timestamp, profile)`:
    ```python
    if profile in [FOREX, FUTURES] and timestamp.hour >= 20:
        return (timestamp + 4 hours).date()
    return timestamp.date()
    ```

### Auditor Update
- Refactor `PortfolioAuditor` in `validate_portfolio_artifacts.py` to use `to_market_date`.
- Ensure `detect_gaps` uses the same logic to maintain consistency between storage and auditing.
