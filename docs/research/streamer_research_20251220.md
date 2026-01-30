# Research Report: Real-Time Data Streamer & Lakehouse Feasibility

## 1. WebSocket Schema Mapping (`qsd` message)
Analysis of raw packets from `data.tradingview.com` reveals the following field mapping for real-time quote updates:

| Field | Meaning | Type | Note |
| :--- | :--- | :--- | :--- |
| `lp` | Last Price | Float | The most recent traded price. |
| `lp_time` | Last Price Time | Unix TS | Precision: Seconds. |
| `volume` | 24h Volume | Float | Cumulative rolling 24h volume. |
| `ch` | Change | Float | Absolute price change. |
| `chp` | Change % | Float | Percentage price change. |
| `bid` | Best Bid | Float | Highest buy order (if available). |
| `ask` | Best Ask | Float | Lowest sell order (if available). |

## 2. Resolution Analysis: Snapshots vs. Ticks
*   **Actual Resolution:** The API provides **Snapshots**, not individual **Ticks**. Multiple trades occurring within the same 1-second window are aggregated into a single `lp` update.
*   **Latency:** Updates arrive at approximately **1-second intervals** for high-liquidity crypto pairs (`BTCUSDT`).
*   **Volume:** The `volume` field is cumulative. To derive "interval volume," one must calculate the delta between consecutive packets.

## 3. Data Lakehouse Feasibility
Building a "Crypto Data Lakehouse" using this API is **feasible but limited**:

### Pros
*   **Zero Infrastructure Cost:** Leverages TradingView's consolidated data streams without needing direct exchange API management.
*   **Normalized Schemas:** Consistent data format across different exchanges (Binance, OKX, Bybit).
*   **Indicator Ingestion:** Ability to ingest calculated indicators (RSI, MACD) in real-time alongside price.

### Cons
*   **Not True Tick Data:** Unsuitable for High-Frequency Trading (HFT) research requiring individual trade sizes and exact sequence.
*   **Reconnection Gaps:** WebSocket drops result in data gaps. While the library has a `RetryHandler`, it does not support "gap fill" from historical data automatically.
*   **Unauthorized Token Limits:** Heavy reliance on "unauthorized_user_token" may lead to IP-based rate limiting for high-throughput ingestion.

### Recommended Architecture
1.  **Ingestion:** Python-based `Streamer` processes writing to **Apache Iceberg** tables.
2.  **Storage:** Partition by `symbol` and `date`.
3.  **Format:** Use **Parquet** for efficient analytical queries.
4.  **Scaling:** Deploy multiple ingestion workers (one per exchange) to avoid connection bottlenecks.

## 4. Conclusion
This API is an excellent source for **1-second or 1-minute high-resolution OHLCV** data lakehouses. It is **not** a replacement for raw exchange Tick/L3 data. For institutional trend-following and mean-reversion research, the resolution is more than sufficient.
