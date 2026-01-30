# Design: Constituent-Level Parity Audit (v1)

## 1. Objective
To isolate the root cause of rating divergence by auditing the parity of individual technical indicators (constituents) rather than just the composite rating.

## 2. Methodology
Instead of comparing only `Recommend.All`, we will fetch the raw values of the underlying indicators from the TradingView Screener API and compare them against `pandas-ta` outputs.

### 2.1 Target Constituents
We will audit the following key indicators:
- **RSI (14)**: `RSI`
- **MACD (12, 26, 9)**: `MACD.macd`, `MACD.signal`
- **Stochastic (14, 3, 3)**: `Stoch.K`, `Stoch.D`
- **ADX (14)**: `ADX`
- **SMA (50)**: `SMA50`
- **EMA (50)**: `EMA50`
- **Ichimoku**: `Ichimoku.BLine` (Base Line)

## 3. Data Sourcing Protocol
Update `audit_feature_parity.py` to request these specific columns from the `Screener` API.

| Replicated (Pandas-TA) | TradingView Column |
| :--- | :--- |
| `ta.rsi(close, 14)` | `RSI` |
| `ta.macd(...)["MACD_..."]` | `MACD.macd` |
| `ta.stoch(...)["STOCHk..."]` | `Stoch.K` |
| `ta.adx(...)["ADX_14"]` | `ADX` |

## 4. TDD Strategy
- **`tests/test_constituent_extraction.py`**:
    - Verify that the updated audit script can correctly parse the expanded column set.
    - Verify that the comparison logic handles `None` values gracefully.

## 5. Success Criteria
- Identify at least one indicator with > 1% divergence to target for specific tuning.
- Confirm high parity (> 0.99 correlation) for standard indicators like SMA/EMA.
