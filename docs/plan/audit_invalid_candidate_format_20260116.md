# Audit Plan: Invalid Candidate Format Warning (2026-01-16)

## 1. Issue Description
**Log**: `2026-01-16 21:58:10,658 - WARNING - Skipping invalid candidate format: {'index': 366, 'timestamp': 1766016000.0, ...}`
**Context**: Hundreds of these warnings appear during the `data-ingest` stage of the production pipeline.
**Root Cause**: 
1.  `scripts/services/ingest_data.py` iterates over all `.json` files in the export directory.
2.  `tradingview_scraper.symbols.stream.persistent_loader.PersistentDataLoader` initializes `Streamer` with `export_result=True`.
3.  When `ingest_data.py` fetches missing data (e.g., for `PENGUUSDT`), `PersistentDataLoader` triggers `Streamer`, which inadvertently saves the raw OHLC data to a JSON file (e.g., `ohlc_penguusdt_20260116-215605.json`) in the same export directory.
4.  The `find` command in the Makefile (or a subsequent process) picks up this new OHLC file and passes it to `ingest_data.py`.
5.  `ingest_data.py` expects a list of candidate dictionaries (with `symbol` key), but receives a list of OHLC bars, triggering the validation warning for every bar.

## 2. Impact Analysis
- **Data Integrity**: **Safe**. The valid candidate files are processed correctly. The OHLC files are simply skipped by the validation logic.
- **Performance**: **Low Impact**. Minimal overhead from writing/reading the extra JSON file and logging warnings.
- **Observability**: **High Noise**. The logs are flooded with false-positive warnings, obscuring real issues.

## 3. Remediation Plan

### 3.1 Code Fix
Disable the automatic JSON export in `PersistentDataLoader`. The loader's primary responsibility is persisting to the Lakehouse (Parquet), not exporting raw JSONs.

**File**: `tradingview_scraper/symbols/stream/persistent_loader.py`
**Change**:
```python
# Before
self.streamer = Streamer(export_result=True, websocket_jwt_token=websocket_jwt_token)

# After
self.streamer = Streamer(export_result=False, websocket_jwt_token=websocket_jwt_token)
```

### 3.2 Cleanup (Optional)
Update `scripts/services/ingest_data.py` to explicitly ignore files starting with `ohlc_` or strictly validate the JSON structure before iterating (Fail Fast).

## 4. Verification
1.  Apply the fix to `PersistentDataLoader`.
2.  Run a test ingestion (e.g., `make data-ingest`) on a profile.
3.  Verify that no `ohlc_*.json` files are created in the export directory.
4.  Verify that no "Skipping invalid candidate format" warnings appear in the logs.
