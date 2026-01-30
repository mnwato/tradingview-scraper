# Validation Plan: Invalid Candidate Format Fix (2026-01-16)

## 1. Objective
Validate that setting `export_result=False` in `PersistentDataLoader` prevents the creation of rogue `ohlc_*.json` files in the export directory, thereby eliminating the "Invalid Candidate Format" warnings during data ingestion.

## 2. Prerequisites
- **Codebase State**: Fix applied to `tradingview_scraper/symbols/stream/persistent_loader.py`.
- **Environment**: Access to `uv` and `make`.

## 3. Execution Steps

### 3.1 Apply Fix
Modify `tradingview_scraper/symbols/stream/persistent_loader.py`:
```python
# Change line 34
self.streamer = Streamer(export_result=False, websocket_jwt_token=websocket_jwt_token)
```

### 3.2 Cleanup Artifacts
Remove existing rogue export files to ensure a clean test environment.
```bash
rm -f export/*/ohlc_*.json
```

### 3.3 Verification Run
Execute a targeted data ingestion for a known symbol (e.g., `BINANCE:BTCUSDT` or a fresh symbol if possible) to trigger the loader.
Since we want to trigger a fetch, we might need to simulate a "stale" condition or just run a quick check.
For simplicity, we will run the unit test `tests/test_persistent_loader.py` if it exists, or run a small `ingest_data.py` command.

**Command**:
```bash
# Create a dummy candidate file
echo '{"data": [{"symbol": "BINANCE:BTCUSDT"}]}' > temp_candidates.json

# Run ingest (this uses PersistentDataLoader)
uv run scripts/services/ingest_data.py --candidates temp_candidates.json
```

### 3.4 Outcome Verification
1.  **Check Export Directory**: Ensure NO `ohlc_*.json` files are created in `export/` (or the run-specific export dir).
2.  **Check Logs**: Confirm `ingest_data.py` does not log "Skipping invalid candidate format".

## 4. Rollback Plan
If the fix causes regression (e.g., data not loading), revert the change to `export_result=True`.
