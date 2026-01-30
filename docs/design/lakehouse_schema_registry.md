# Lakehouse Schema Registry v1

## 1. Overview
This document serves as the authoritative registry for all data schemas within the Quantitative Data Lakehouse. It defines the structure, data types, and constraints for both Structured (Parquet) and Unstructured (Lance) data.

## 2. Structured Data (Parquet)
Managed by the `Data Cycle` (`flow-data`). Stored in `data/lakehouse/`.

### 2.1 Market Data (OHLCV)
*   **Path Pattern**: `data/lakehouse/{EXCHANGE}_{SYMBOL}_1d.parquet`
*   **Update Frequency**: Daily
*   **Retention**: Permanent (SCD Type 2 not required, append-only/overwrite)

| Column | Type | Description | Constraints |
| :--- | :--- | :--- | :--- |
| `timestamp` | `int64` | Unix timestamp (seconds) | UTC, Daily granularity (00:00:00) |
| `open` | `float64` | Open price | > 0 |
| `high` | `float64` | High price | >= Open, >= Close, >= Low |
| `low` | `float64` | Low price | <= Open, <= Close, <= High, > 0 |
| `close` | `float64` | Close price | > 0 |
| `volume` | `float64` | Trading volume (Base unit) | >= 0 |

### 2.2 Structural Metadata (Symbol Definition)
*   **Path**: `data/lakehouse/symbols.parquet`
*   **Source**: TradingView API (`scripts/build_metadata_catalog.py`)
*   **Versioning**: SCD Type 2 (Valid From/To)

| Column | Type | Description |
| :--- | :--- | :--- |
| `symbol` | `string` | Unified symbol (e.g. `BINANCE:BTCUSDT`) |
| `exchange` | `string` | Exchange code (e.g. `BINANCE`) |
| `base` | `string` | Base currency/asset |
| `quote` | `string` | Quote currency/asset |
| `type` | `string` | Asset type (`spot`, `swap`, `futures`, `index`) |
| `profile` | `string` | Data profile (`CRYPTO`, `EQUITY`, etc.) |
| `description` | `string` | Human readable description |
| `sector` | `string` | Sector classification |
| `pricescale` | `int64` | Price precision (10^x) |
| `minmov` | `int64` | Minimum price movement unit |
| `tick_size` | `float64` | Calculated `minmov / pricescale` |
| `timezone` | `string` | Exchange timezone (e.g. `UTC`) |
| `active` | `bool` | Is actively trading |
| `valid_from` | `timestamp` | SCD2 Start |
| `valid_until` | `timestamp` | SCD2 End (Null if current) |

### 2.3 Execution Metadata (Venue Limits)
*   **Path**: `data/lakehouse/execution.parquet`
*   **Source**: CCXT / Exchange Info (`scripts/fetch_execution_metadata.py`)
*   **Key**: `symbol` + `venue`

| Column | Type | Description |
| :--- | :--- | :--- |
| `symbol` | `string` | Unified symbol |
| `venue` | `string` | Execution venue (e.g. `BINANCE`) |
| `lot_size` | `float64` | Minimum quantity step |
| `min_notional` | `float64` | Minimum order value ($) |
| `step_size` | `float64` | Quantity precision step |
| `maker_fee` | `float64` | Maker fee rate (e.g. 0.001) |
| `taker_fee` | `float64` | Taker fee rate (e.g. 0.001) |
| `updated_at` | `timestamp` | Last update timestamp |

### 2.4 Exchange Metadata
*   **Path**: `data/lakehouse/exchanges.parquet`
*   **Source**: TradingView / Static Config

| Column | Type | Description |
| :--- | :--- | :--- |
| `exchange` | `string` | Exchange Code |
| `country` | `string` | Jurisdiction |
| `is_crypto` | `bool` | Crypto flag |
| `timezone` | `string` | Timezone |

## 3. Unstructured Data (Lance) - *Future*
To be implemented using LanceDB for vector storage and fast retrieval of unstructured signals.

### 3.1 News & Sentiment
*   **Target Path**: `data/lakehouse/news.lance`
*   **Schema Candidate**:
    *   `timestamp`: `timestamp`
    *   `symbol`: `string`
    *   `headline`: `string`
    *   `source`: `string`
    *   `embedding`: `vector(768)` (e.g. BERT/Transformer embedding)
    *   `sentiment_score`: `float32`

## 4. Feature Store (Time-Series Features)
Managed by the `Feature Ingestion Service`. Stored in `data/lakehouse/features/`.

### 4.1 TradingView Technicals
*   **Path**: `data/lakehouse/features/tv_technicals_1d.parquet` (Partitioned by Date)
*   **Source**: TradingView Scanner API (`scripts/services/ingest_features.py`)
*   **Frequency**: Daily Snapshot

| Column | Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `int64` | Ingestion Time (UTC) |
| `symbol` | `string` | Unified Symbol |
| `recommend_all` | `float32` | Composite Rating (-1.0 to 1.0) |
| `recommend_ma` | `float32` | MA Rating |
| `recommend_other` | `float32` | Oscillator Rating |
| `rsi` | `float32` | RSI(14) |
| `adx` | `float32` | ADX(14) |
| `volatility_d` | `float32` | Daily Volatility |
| `perf_w` | `float32` | Weekly Performance % |
| `perf_1m` | `float32` | Monthly Performance % |

## 5. Integrity Constraints
1.  **Toxic Data Guard**: Market Data ingestion MUST reject daily returns > 500% (`TOXIC_THRESHOLD`).
2.  **Referential Integrity**: All symbols in `execution.parquet` and `features/*` MUST exist in `symbols.parquet`.
3.  **Idempotency**: Ingestion scripts MUST be re-runnable without duplicating data.
