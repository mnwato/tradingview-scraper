# Research Report: Data Schema Normalization & Tardis.dev Comparison

## 1. Current Schema Audit
### OHLCV (Streamer)
The `Streamer` class produces the following JSON structure for historical candles:
```json
{
  "index": 0,
  "timestamp": 1672531200,
  "open": 16500.5,
  "high": 16550.0,
  "low": 16480.0,
  "close": 16525.0,
  "volume": 1250.5
}
```

### Overview (Metadata)
The `Overview` class provides a rich set of metadata fields, including:
*   `price_earnings_ttm`
*   `market_cap_basic`
*   `total_revenue`
*   `sector`
*   `industry`

## 2. Industry Standard Comparison (Gap Analysis)

| Field | TradingView Scraper | Tardis.dev (Trade) | Cryptofeed (Candle) | Gap / Note |
| :--- | :--- | :--- | :--- | :--- |
| **Timestamp** | `timestamp` (Unix Sec) | `timestamp` (Microseconds) | `timestamp` (Float) | **Resolution Mismatch:** TV provides seconds, others use micro/milliseconds. |
| **Symbol** | `EXCHANGE:SYMBOL` | `symbol` (e.g. BTC-USDT) | `symbol` (e.g. BTC-USDT) | **Format Mismatch:** TV uses colon separator. |
| **Open/High/Low/Close** | `open`, `high`, `low`, `close` | N/A (Trade-level) | `open`, `high`, `low`, `close` | **Aligned:** Standard OHLC naming. |
| **Volume** | `volume` | `amount` | `volume` | **Ambiguity:** TV volume is often base asset, but can vary by exchange. |
| **Trade Count** | **MISSING** | `id` (Trade ID) | `count` | **Critical Gap:** TV does not provide number of trades per candle. |
| **VWAP** | **MISSING** | Derived | `vwap` | **Gap:** Can be fetched as an indicator but not in default OHLC. |
| **Open Interest** | **MISSING** | `open_interest` | `open_interest` | **Gap:** Crucial for derivatives, available only via specific indicators. |
| **Funding Rate** | **MISSING** | `funding_rate` | `funding` | **Gap:** Essential for perp analysis. |
| **Side** | N/A | `side` (buy/sell) | N/A | **N/A:** TV provides aggregated candles, not individual trades. |

## 3. Schema Evolution Proposal
To align with "Tardis-Lite" standards, we propose a `NormalizedCandle` model:

```python
class NormalizedCandle(BaseModel):
    exchange: str
    symbol: str
    timestamp_ms: int  # Converted from TV seconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    # Enriched Fields (Optional/Calculated)
    vwap: Optional[float]
    trade_count: Optional[int] # Likely unavailable
    is_complete: bool = True
```

## 4. Conclusion
While the library excels at structural OHLCV data, it lacks the trade-level granularity (Side, Trade ID) and derivative-specific metadata (OI, Funding) found in Tardis or Cryptofeed. It is best positioned as a **"Macro/Structural" data source** rather than a tick-level replay engine.
