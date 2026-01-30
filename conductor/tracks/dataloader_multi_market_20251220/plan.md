# Implementation Plan: DataLoader Multi-Market Testing & Sample Datasets

## Phase 1: Multi-Market Test Suite Development [checkpoint: da0300d]
Goal: Create a robust test suite to validate `DataLoader` across diverse asset classes.

- [x] Task: Create `tests/test_dataloader_markets.py` with test cases for:
    - Crypto: `BINANCE:BTCUSDT`
    - Forex: `FX_IDC:EURUSD`
    - Stocks: `NASDAQ:AAPL`
    - Indices: `SP:SPX`
    - Commodities: `COMEX:GC1!`
- [x] Task: Implement validation checks for data continuity and timestamp alignment in each market.
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Sample Data Generation & Quality Audit [checkpoint: da0300d]
Goal: Generate high-quality sample datasets for documentation and benchmarking.

- [x] Task: Run the multi-market suite and export successful loads to `export/samples/` (Verified in `export/ohlc_*`).
- [x] Task: Audit the quality of samples (e.g., check for holiday gaps in Stocks vs. 24/7 Crypto).
- [x] Task: Document specific symbol prefixes required for each market (e.g., `COMEX:` for Gold).
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Documentation & Library Finalization [checkpoint: da0300d]
Goal: Finalize the `DataLoader` as a production-ready component for multi-market backtesting.

- [x] Task: Update `docs/research/historical_loader_20251220.md` with verified multi-market support.
- [x] Task: Add "Multi-Market Usage" examples to the main `README.md`.
- [x] Task: Conductor - User Manual Verification 'Phase 3'