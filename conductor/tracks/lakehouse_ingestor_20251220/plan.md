# Implementation Plan: Data Lakehouse Ingestor & Persistent DataLoader

## Phase 1: Storage Layer & Schema Definition [checkpoint: 32835b5]
Goal: Implement a robust local storage backend for crypto history using Parquet.

- [x] Task: Research and implement `LakehouseStorage` class using `pandas`.
- [x] Task: Define the unified schema for OHLCV + Metadata (Exchange, Symbol, Interval).
- [x] Task: Implement deduplication logic to handle overlapping data fetches.
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Persistent DataLoader Wrapper [checkpoint: 32835b5]
Goal: Create a wrapper that intelligently merges local history with fresh API fetches.

- [x] Task: Implement `PersistentDataLoader.load(symbol, start, end, interval)`.
- [x] Task: Add logic to identify "Gaps" between local storage and requested range (Implemented via fallback logic).
- [x] Task: Implement "Exceed Limit" handling: If requested range > 8500 candles, load what's available and warn the user.
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Forward-Accumulation Ingestor (Hybrid Strategy) [checkpoint: 32835b5]
Goal: Automate the incremental building of the Data Lakehouse.

- [x] Task: Implement `PersistentDataLoader.sync(symbol, interval)` to fetch only the delta from last local timestamp to now.
- [x] Task: Create `scripts/run_lakehouse_sync.py` to demonstrate synchronizing the Binance Top 5.
- [x] Task: Document the "Hybrid ITD" approach (immediate 1d/1h backfill + forward 1m accumulation).
- [x] Task: Conductor - User Manual Verification 'Phase 3'