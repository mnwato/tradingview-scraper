# Feature Store Architecture v1

## 1. Overview
The **Feature Store** centralizes signal data (Technical Indicators, Sentiment, Ratings) in the Lakehouse, separating feature engineering/ingestion from consumption.

## 2. Feature Types

### 2.1 TradingView Technicals (Source: TV Scanner API)
These are computed fields provided by TradingView.
*   **Update Frequency**: Daily (snapshot at ingestion time).
*   **Storage**: `data/lakehouse/features/tv_technicals_1d.parquet`
*   **Schema**:
    *   `timestamp` (int64): Ingestion time (UTC).
    *   `symbol` (string): Unified symbol.
    *   `Recommend.All` (float): Composite rating (-1.0 to 1.0).
    *   `Recommend.MA` (float): Moving Average rating.
    *   `Recommend.Other` (float): Oscillator rating.
    *   `RSI` (float): Relative Strength Index (14).
    *   `ADX` (float): Average Directional Index (14).
    *   `AO` (float): Awesome Oscillator.
    *   `CCI20` (float): Commodity Channel Index.
    *   `Stoch.K` (float): Stochastic K.
    *   `Stoch.D` (float): Stochastic D.
    *   `MACD.macd` (float): MACD Level.
    *   `MACD.signal` (float): MACD Signal.
    *   `Volatility.D` (float): Daily Volatility.
    *   `Perf.W` (float): Weekly Performance (%).
    *   `Perf.1M` (float): Monthly Performance (%).

### 2.2 Locally Engineered Features (Future)
Computed from OHLCV data in the Lakehouse.
*   **Storage**: `data/lakehouse/features/local_1d.parquet`
*   **Examples**: `returns_1d`, `volatility_20d`, `momentum_60d`.

## 3. Ingestion Strategy

### 3.1 Service: `scripts/services/ingest_features.py`
*   **Trigger**: Runs as part of `flow-data` (after `data-ingest` and `meta-ingest`).
*   **Input**: `portfolio_candidates.json` (or full active universe).
*   **Operation**:
    1.  Batches symbols.
    2.  Calls TradingView Scanner API (`Overview.get_symbol_overview` or bulk scanner endpoint).
    3.  Appends rows to the daily partition of `tv_technicals_1d.parquet`.

### 3.2 Access Pattern (Point-in-Time)
*   **Training**: Join features to target variables based on `timestamp`.
*   **Inference (Selection)**: Query `latest` snapshot for current signals.

## 4. Lakehouse Schema Update
We extend the Registry to include the Feature Store.

### 4.1 Path Structure
```text
data/lakehouse/
├── features/
│   ├── tv_technicals_1d/  (Partitioned Parquet Dataset)
│   │   └── date=2026-01-16/
│   │       └── part-0.parquet
```

## 5. Migration Plan
1.  **Define Schema**: Update `lakehouse_schema_registry.md`.
2.  **Implement Ingestor**: Create `ingest_features.py`.
3.  **Update Orchestrator**: Add feature ingestion to `flow-data`.
