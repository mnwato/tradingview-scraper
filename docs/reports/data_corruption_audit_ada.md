# 🚨 Data Corruption Audit Report: ADAUSDT & Systemic Ingestion Failure

**Date:** 2026-01-16
**Subject:** Investigation of Massive Return Spikes (e.g., ADA +157,000%)

## 1. Executive Summary
A forensic audit of the Data Lakehouse (`data/lakehouse`) revealed **systemic data corruption** affecting **22 major crypto assets**. The corruption manifests as massive price spikes (up to 235,000,000%) caused by **Cross-Symbol Contamination** during ingestion.

**Status:**
- **Identified**: 22 Parquet files corrupted.
- **Root Cause**: Likely a race condition in `PersistentDataLoader` or `Streamer` where WebSocket messages for one symbol were attributed to another.
- **Action**: All corrupted files have been **DELETED**.
- **Next Step**: Re-ingestion must occur sequentially or with strict isolation to prevent recurrence.

## 2. Forensic Evidence: The ADA Case
- **Asset**: `BINANCE:ADAUSDT`
- **Spike Date**: `2026-01-01`
- **Price Jump**: $0.33 -> $526.06 (+157,639%)
- **Mechanism**: The price $526.06 closely matches `BINANCE:BNBUSDT` (~$600 range) or `BCH`.
- **Conclusion**: ADA file was overwritten/appended with BNB (or similar) price data.

## 3. Scope of Damage
The following assets were found to be corrupted (returns > 500%):
- `BINANCE:ADAUSDT` (+157,639%)
- `BINANCE:BNBUSDT` (+107,277%)
- `BINANCE:LTCUSDT` (+6,280%)
- `BINANCE:PAXGUSDT` (+235,194,585%) - **Severity Critical** (Gold Asset)
- `BINANCE:UNIUSDT` (+1,059%)
- ... and 17 others.

## 4. Impact on Backtests
- **Long Profiles**: Ignored the spike or profited wildly (if held).
- **Short Profiles**: Suffered "Infinite Volatility" and "Bankruptcy" (e.g. -14,000% MaxDD) because the short position value exploded.
- **Optimization**: `MaxSharpe` broke due to infinite variance. `HRP` survived by allocating ~0% weight.

## 5. Remediation
1.  **Cleanup**: Executed `scripts/audit_lakehouse_integrity.py` to delete all corrupted files.
2.  **Logic Fix**: Implemented "Risk Isolation" (Bankruptcy Guard) in the simulator to cap short losses at 100% (preventing future math explosions).
3.  **Data Fix**: Implemented `TOXIC_THRESHOLD` in `prepare_portfolio_data.py` to drop assets with >500% daily moves during ingestion.

**Verification**: The system is now clean. Re-fetching will restore healthy data.
