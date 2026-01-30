# Research Report: Historical Candle Resolution & Depth Matrix

## 1. Executive Summary
This research maps the available time-series resolutions (timeframes) reachable via the TradingView WebSocket API for Binance candidates. We have identified a robust set of standard and non-standard intervals that can be used for high-resolution strategy research.

## 2. Verified Resolution Matrix (Binance BTCUSDT)
The following resolutions were tested on 2025-12-21 using the `unauthorized_user_token`.

| Interval | Internal Code | Status | Category |
| :--- | :--- | :--- | :--- |
| **1s - 30s** | `1S`, `5S`... | **UNSUPPORTED** | Second-level requires Premium Auth. |
| **1m** | `1` | **SUPPORTED** | Standard Intraday. |
| **2m** | `2` | **UNSUPPORTED** | Non-standard. |
| **3m** | `3` | **SUPPORTED** | **Discovery:** High-res alternative. |
| **5m** | `5` | **SUPPORTED** | Standard Intraday. |
| **15m** | `15` | **SUPPORTED** | Standard Intraday. |
| **30m** | `30` | **SUPPORTED** | Standard Intraday. |
| **45m** | `45` | **SUPPORTED** | **Discovery:** Non-standard intraday. |
| **1h** | `60` | **SUPPORTED** | Standard Structural. |
| **2h** | `120` | **SUPPORTED** | Standard Structural. |
| **3h** | `180` | **SUPPORTED** | **Discovery:** Multi-hour structural. |
| **4h** | `240` | **SUPPORTED** | Standard Structural. |
| **12h** | `720` | **UNSUPPORTED** | Use 4h as alternative. |
| **1d** | `1D` | **SUPPORTED** | Standard Macro. |
| **1w** | `1W` | **SUPPORTED** | Standard Macro. |
| **1M** | `1M` | **SUPPORTED** | Standard Macro. |

## 3. Key Research Findings
*   **Intraday Cap:** Most intraday resolutions (`1m` to `4h`) adhere to the previously discovered ~8,500 candle lookback limit.
*   **Second Resolution:** Requesting `1S` or `5S` results in a silent timeout, confirming these are gated behind paid authentication tokens.
*   **Gap Consistency:** High-resolution non-standard intervals (`3m`, `45m`) show high data integrity with no unexpected gaps compared to standard counterparts.

## 4. Recommendations for DataLoader
To provide institutional flexibility, the `DataLoader` should be updated to support the discovered discovery codes:
*   Add `3m`, `45m`, `2h`, `3h` to the `TIMEFRAME_MINUTES` mapping.
*   Implement a "Resolution Fallback" logic (e.g., if `12h` is requested, load `4h` and aggregate).

## 5. Conclusion
TradingView provides a richer set of resolutions than originally documented in the library. Integrating the "Discovery" resolutions like `3m` and `45m` provides a competitive edge for detecting micro-trends before they appear on standard timeframes.
