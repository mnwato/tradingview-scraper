# Design: Discovery Scanner Hardening (v1)

## 1. Objective
To enhance the reliability and "Alpha-Readiness" of discovery scanners by integrating advanced microstructure validation and ensuring strict data contracts during the initial candidate sourcing phase.

## 2. Integrated Sanity Gates

### 2.1 The "First-Batch" Veto
Currently, scanners retrieve data and pass it to a post-processor. We will implement a mandatory validation step within the `discover()` method of each scanner.

- **Trigger**: Immediately after the first set of OHLCV data is retrieved for a candidate.
- **Logic**: Apply `AdvancedToxicityValidator.is_volume_toxic` and `is_price_stalled`.
- **Outcome**: If a candidate fails, it is dropped immediately and NOT included in the discovery export. This prevents DataOps from even attempting to ingest known toxic assets.

### 2.2 Registry-Aware Discovery
Scanners must respect the historical "blacklist" maintained by the platform.

1.  Load `FoundationHealthRegistry`.
2.  Filter the initial candidate list:
    - If `symbol` has status `toxic` AND `reason` is persistent (e.g., microstructure breakdown), skip.
    - If `symbol` was previously dropped due to a temporary gap, allow re-scan.

## 3. Standardized Audit Trail
Scanners will move away from local `AuditLedger` instances.

- **Span-based Logging**: Use `@trace_span` on `discover()`.
- **Event Injection**: Record discovery events (e.g., `AssetDropped`, `ScannerError`) directly into the active OpenTelemetry span.

## 4. Implementation Details

### 4.1 TradingView Scanner Refactor
Update `TradingViewDiscoveryScanner.discover()`:
- Pass `FoundationHealthRegistry` to `FuturesUniverseSelector` (or filter after).
- Implement a `validation_gate` callback that uses `AdvancedToxicityValidator`.

### 4.2 Binance Scanner Update
Update `BinanceDiscoveryScanner.discover()`:
- Add a 20-day volume check for each candidate before adding it to the export.

## 5. TDD Strategy
- **`tests/test_scanner_hardening.py`**:
    - Mock a TradingView screen that returns one healthy and one toxic asset.
    - Verify that only the healthy asset is exported.
    - Verify that toxic assets are recorded in the span attributes.
