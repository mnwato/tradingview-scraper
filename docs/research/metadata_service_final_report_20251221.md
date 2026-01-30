# Final Report: Metadata Service Architecture & PIT Design
**Date:** 2025-12-21
**Author:** Jules

## 1. Executive Summary
This research track established the design for a "Data Lakehouse Metadata Catalog" capable of storing symbol definitions, structural metadata (tick size, contract details), and preventing look-ahead bias through Point-in-Time (PIT) versioning.

## 2. Architecture

### A. Storage
- **Symbol Catalog**: `data/lakehouse/symbols.parquet`
- **Exchange Catalog**: `data/lakehouse/exchanges.parquet`
- **Schema (Symbols)**:
    - `symbol` (PK), `exchange`, `base`, `quote`, `type`, `subtype`, `profile` (persisted DataProfile).
    - **Descriptive**: `description`, `sector`, `industry`, `country`.
    - **Contextual**: `timezone`, `session` (API-synced when available; defaults only when API returns `None`).
    - **Structural**: `tick_size`, `minmov`, `pricescale`, `lot_size`, `contract_size`.
    - **Versioning**: `valid_from`, `valid_until`, `updated_at`, `active`.

- **Schema (Exchanges)**:
    - `exchange` (PK), `country`, `timezone`, `is_crypto`, `description`, `updated_at`.

### B. Versioning (SCD Type 2)
To support accurate backtesting:
- Updates to a symbol do **not** overwrite the existing record.
- The old record is "retired" by setting `valid_until = NOW`.
- A new record is inserted with `valid_from = NOW`.
- Lookups take an optional `as_of` timestamp to retrieve the metadata state at any historical point.

### C. Hybrid Sourcing
- **TradingView**: Primary source for universe discovery, symbol classification, descriptive metadata, and price structure (`pricescale`, `minmov`).
- **Exchange APIs (Planned)**: Will enrich the catalog with execution-specifics like `lot_size` and `min_notional`.

## 3. Implementation Status

- [x] **Core Catalog**: `MetadataCatalog` and `ExchangeCatalog` implemented in `tradingview_scraper/symbols/stream/metadata.py`.
- [x] **Enriched Metadata**: `description`, `sector`, `industry`, `country`, `timezone`, `session` now captured.
- [x] **PIT Support**: `valid_from`/`valid_until` logic and `get_instrument(..., as_of=ts)` implemented and tested.
- [x] **Build Script**: `scripts/build_metadata_catalog.py` created to bootstrap both catalogs.
- [x] **Ingestion Integration**: `PersistentDataLoader` now automatically checks and attempts to enrich descriptive metadata during sync.

## 4. Audit & Data Quality
A systematic audit was performed (`scripts/audit_metadata_catalog.py`) comparing the local catalog against live TradingView API responses.

### Findings:
- **Consistency**: 100% match on structural fields (`pricescale`, `minmov`) for refreshed records.
- **Enrichment**: Successfully backfilled `description` and `timezone` for the Binance Top 50 universe.
- [x] **API Optimization**: The `Overview` class was updated to include `STRUCTURAL_FIELDS` in its default `ALL_FIELDS` list, ensuring all future lookups capture essential metadata without explicit field requests.

## 5. Point-in-Time (PIT) & Lifecycle Management
The system implements a strict **Slowly Changing Dimension (SCD) Type 2** pattern to manage instrument lifecycles and prevent look-ahead bias.

### Key Features:
- **Contiguous History**: Version transitions are atomic; the `valid_until` of an old record exactly matches the `valid_from` of the new record.
- **Delisting Support**: The `retire_symbols` method enables safe deactivation of instruments. Instead of deletion, a new record is created with `active=False`, preserving the ability to backtest against the instrument during its active period.
- **Integrity Verified**: Systematic audits (`scripts/audit_metadata_pit.py`) confirm 100% contiguity and uniqueness of active records.

## 6. Recommendations for Next Phase
1.  **Exchange Integration**: Build a "Connector" module to fetch execution limits from Binance/OKX APIs to fill the `None` values in the catalog.
2.  **Backtest Integration**: Update the Backtesting engine to query `MetadataCatalog` with `as_of=candle.timestamp` to ensure accurate tick-size/lot-size simulation.
3.  **Scheduled Maintenance**: Run `scripts/build_metadata_catalog.py` (or a more advanced "Audit" script) daily to capture changes in the universe (e.g., delistings).

## 7. Amendments (2025-12-28)
- **Persist `profile`**: Store `profile` in `symbols.parquet` as a versioned field so historical classifications remain stable even if derivation heuristics evolve.
- **Build on existing catalogs**: Prefer incremental refresh/upsert; do not delete `symbols.parquet`/`exchanges.parquet` in production/backtesting workflows.
- **Session/timezone resolution**: Ensure all writers (batch build + runtime auto-enrichment) follow the same hierarchy (API -> exchange defaults -> fallback).
