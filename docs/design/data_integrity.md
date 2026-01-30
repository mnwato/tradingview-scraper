# Design Document: Data Integrity & Institutional Alignment

## 1. Overview
This document formalizes the data integrity standards for the Quantitative Portfolio Platform, focusing on institutional session alignment, gap detection, and heartbeat resilience.

## 2. Market-Day Normalization
Legitimate trading sessions often span multiple UTC days. A naive UTC date extraction leads to false-positive data gaps (e.g., "Missing Friday" or "Missing Monday" alerts).

### Standard: The +4 Hour Shift
For `FOREX` and `FUTURES` data profiles, timestamps between **20:00 and 23:59 UTC** are normalized to the **next calendar day** for auditing purposes.
- **Example**: A Forex bar at `Thursday 22:00 UTC` represents the **Friday** session.
- **Example**: A Futures bar at `Sunday 21:00 UTC` represents the **Monday** session.

### Standard: 1-Session Institutional Tolerance
Many exchanges have "technical" sessions on bank holidays (e.g., MLK Day, Good Friday) where TradingView or regional providers do not provide data. 
- **Policy**: Gaps that are **exactly 1 session** in length according to the institutional calendar are **ignored**.
- This ensures the pipeline doesn't drop diversifiers due to localized exchange dropouts that are statistically insignificant for daily optimization.

## 3. Institutional Calendar Mapping
Every exchange must be mapped to its canonical regional calendar to avoid US-centric holiday bias.

| Exchange (TV) | Canonical Calendar | Region |
| :--- | :--- | :--- |
| `EUREX` | `XFRA` (Frankfurt) | Europe |
| `NSE` | `XNSE` (Mumbai) | India |
| `CME`, `CBOT`, `NYMEX` | `CMES` (CME Standard) | USA |
| `ICEUS` | `ICEUS` | USA |
| `FOREX` Brokers | `24/5` (Custom/XCME proxy) | Global |

## 4. Heartbeat & Connection Resilience
The WebSocket streamer must distinguish between a "Quiet Market" and a "Dead Connection."

### Idle Packet Detection
- **Limit**: Reconnection is triggered after **5 consecutive heartbeats** (~h~) without interleaved data.
- **Reset**: Any valid JSON data packet resets the idle counter to zero.
- **Timeout**: `ws_timeout` is set to **15.0 seconds** to prevent indefinite blocking on broken sockets.

## 5. Automated Recovery (Self-Healing)
The pipeline enforces a `strict_health` policy.
1.  **Step 8 Health Audit**: Scans all parquet files for gaps using the Market-Day normalization.
2.  **Aggressive Repair**: Triggers `make data-repair` if gaps are found, attempting to backfill with increased retry depth.
3.  **Promotion**: Only assets with 100% integrity (post-normalization) are promoted to the final portfolio candidate pool.
