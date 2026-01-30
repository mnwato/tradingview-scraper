# Audit: Data Pipeline & Scanner Production Readiness (v1)

## 1. Pipeline Overview: The "Golden Path"

The DataOps pipeline follows a strictly ordered sequence to ensure a high-integrity Lakehouse foundation for Alpha generation.

1.  **Discovery (`make scan-run`)**: Identifies candidate symbols via exchange APIs (Binance) and institutional screeners (TradingView).
2.  **Price Ingestion (`make data-ingest`)**: Fetches historical OHLCV data into Parquet format.
3.  **Advanced Validation (`IngestionValidator`)**: Applies toxicity filters (spikes, stalls, ghost candles).
4.  **Metadata Enrichment (`make meta-ingest`)**: Links symbols to tick size, pricescale, and session calendars.
5.  **Feature Computation (`make feature-ingest`)**: Generates technical features (ADX, RSI, etc.).
6.  **PIT Backfill (`make feature-backfill`)**: Standardizes features into a Point-in-Time (PIT) matrix.
7.  **Auto Repair (`make data-repair`)**: Automatically fills gaps discovered during audit.

## 2. Component-Level Audit

### 2.1 TradingView Discovery Scanner
- **Implementation**: `TradingViewDiscoveryScanner` + `FuturesUniverseSelector`.
- **Status**: **PARTIAL PASS**.
- **Identified Issues**:
  - `FuturesUniverseSelector` is monolithic and violates the Single Responsibility Principle.
  - Hardcoded `configs/` literal in `DiscoveryPipeline`.
  - Scanner-level filtering doesn't yet utilize the centralized `AdvancedToxicityValidator`.
  - `FuturesUniverseSelector` handles its own `AuditLedger` which can conflict with parent orchestrators.

### 2.2 Binance Discovery Scanner
- **Implementation**: `BinanceDiscoveryScanner` using CCXT.
- **Status**: **PASS**.
- **Identified Issues**:
  - Lacks volume Z-score awareness during the discovery phase (often picks up newly listed, highly volatile "pump" tokens).

### 2.3 Data Contract Enforcement
- **Implementation**: `IngestionValidator` / `FoundationHealthRegistry`.
- **Status**: **PASS**.
- **Gaps**:
  - Alpha pipelines (`flow-production`) don't yet explicitly veto symbols based on the `FoundationHealthRegistry` before starting; they rely on the `IngestionStage` to drop them silently or fail.

## 3. Remediation Backlog

### High Priority
1.  **Scanner-Validator Integration**: Update all scanners to apply `AdvancedToxicityValidator` on the first batch of data retrieved (early fail-fast).
2.  **Registry-Aware Discovery**: Prevent scanners from even attempting to process symbols already marked as `toxic` in the `FoundationHealthRegistry` in previous runs.

### Medium Priority
1.  **Refactor `FuturesUniverseSelector`**: Break down the monolithic processing logic into smaller, testable `SelectorStage` components.
2.  **Unify Audit Trail**: Standardize all scanners to use the parent's `SelectionContext` for event logging instead of standalone `AuditLedger` instances.

## 4. Conclusion
The pipeline is robust but fragmented. Integrating the scanners more tightly with the newer "Foundation Gates" will eliminate the risk of toxic data propagating through the system and ensure a "Zero-Touch Golden Foundation".
