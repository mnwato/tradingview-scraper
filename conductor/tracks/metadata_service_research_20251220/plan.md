# Implementation Plan: Metadata Service & Lakehouse Catalog Research

## Phase 1: Metadata Requirement Analysis
Goal: Identify all static and dynamic metadata fields required for a robust crypto/multi-asset lakehouse.

- [x] Task: Research standard metadata fields (e.g., `tick_size`, `contract_size`, `listing_date`, `expiry_date`).
- [x] Task: Analyze the `Overview` class output to see which fields are already available from TradingView.
- [x] Task: Document "Gap Fields" that must be sourced externally (e.g., `maker_fee`, `taker_fee`, `delivery_date` for futures).
- [ ] Task: Conductor - User Manual Verification 'Phase 1'
- *See [Research Report](../../../docs/research/metadata_requirements_20251221.md)*

## Phase 2: Catalog Architecture Design
Goal: Design a unified "Metadata Catalog" that serves as the single source of truth for the lakehouse.

- [x] Task: Research Apache Iceberg / Hive Metastore compatibility for symbol metadata.
- [x] Task: Design a `MetadataService` class interface: `get_instrument(symbol)`, `list_active_symbols(exchange)`.
- [x] Task: Propose a storage backend for metadata (e.g., a simple `symbols.parquet` or a dedicated SQLite DB).
- [x] Task: Implement hybrid sourcing strategy (TradingView for discovery + Exchange APIs for execution details).
- [ ] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Prototyping & PIT Research
Goal: Build a prototype metadata extractor and design Point-in-Time (PIT) capabilities to prevent look-ahead bias.

- [x] Task: Research PIT metadata storage strategies (e.g., SCD Type 2 `valid_from`/`valid_until` vs. Snapshots).
- [x] Task: Create `scripts/build_metadata_catalog.py` to build a `symbols.parquet` for the Binance Top 50 (with schema supporting PIT).
- [x] Task: Link `MetadataCatalog` to `PersistentDataLoader` for automated enrichment during ingestion.
- [x] Task: Final Report: Recommended architecture for a lightweight, file-based Metadata Service with PIT support.
- *See [Final Report](../../../docs/research/metadata_service_final_report_20251221.md)*
- [ ] Task: Conductor - User Manual Verification 'Phase 3'
