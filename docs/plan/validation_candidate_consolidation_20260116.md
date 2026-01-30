# Validation Plan: Candidate Consolidation Fix (2026-01-16)

## 1. Objective
Validate that the new `consolidate_candidates.py` script and Makefile integration correctly aggregate individual scanner export files into a master `portfolio_candidates.json` file, enabling the `meta-ingest` step to succeed.

## 2. Prerequisites
- **Codebase State**: `scripts/services/consolidate_candidates.py` created and `Makefile` updated.
- **Environment**: Access to `uv` and `make`.

## 3. Execution Steps

### 3.1 Setup Mock Data
Create a temporary run directory `export/test_consolidation_run/` and populate it with two dummy candidate files to simulate a multi-scanner run.
- `export/test_consolidation_run/scan_A.json`: 2 candidates (BTC, ETH)
- `export/test_consolidation_run/scan_B.json`: 1 candidate (SOL)

### 3.2 Execute Pipeline Step
Run the `data-ingest` make target, which should trigger the ingestion (mocked or real) and then the consolidation.
```bash
make data-ingest RUN_ID=test_consolidation_run
```

### 3.3 Verify Output Artifacts
1.  **Existence**: Check if `data/lakehouse/portfolio_candidates.json` exists.
2.  **Content**: Verify it contains 3 unique candidates (BTC, ETH, SOL).
3.  **Timestamps**: Verify the file was created *after* the make command execution.

### 3.4 Verify Downstream Integration
Execute the `meta-ingest` dependent script to ensure it accepts the generated file.
```bash
uv run scripts/fetch_execution_metadata.py --candidates data/lakehouse/portfolio_candidates.json
```

### 3.5 Edge Case Testing
- **No Files**: Run with an empty export dir. Script should handle gracefully (warn, not crash).
- **Rogue Files**: Ensure `ohlc_*.json` (if any present) are ignored.

## 4. Rollback Plan
If validation fails, revert the `Makefile` changes and investigate the script logic.
