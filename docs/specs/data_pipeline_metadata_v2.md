# Data Pipeline v2: Metadata Ingestion Strategy

## 1. Overview
This document defines the separation of **Metadata Ingestion** (Data Cycle) from **Metadata Enrichment** (Alpha Cycle).

## 2. Problem
Currently, the `flow-production` pipeline includes a `meta-refresh` step which executes `scripts/build_metadata_catalog.py`. This script makes external API calls to TradingView to update the global symbol catalog.
This violates the "Read-Only Alpha Cycle" principle and introduces network fragility into the optimization process.

## 3. Architecture

### 3.1 Data Cycle (`flow-data`)
Responsible for building and maintaining the **Global Metadata Catalog** in the Lakehouse.

*   **Components**:
    1.  **Structural Metadata**: `scripts/build_metadata_catalog.py` (Source: TradingView API).
    2.  **Execution Metadata**: `scripts/fetch_execution_metadata.py` (Source: CCXT/Exchanges).
*   **Artifacts**:
    *   `data/lakehouse/symbols.parquet` (Structural)
    *   `data/lakehouse/execution_metadata.json` (Execution)

### 3.2 Alpha Cycle (`flow-production`)
Responsible for mapping global metadata to the specific candidates of the current run.

*   **Operation**: **Enrichment** (Join).
*   **Script**: `scripts/enrich_candidates_metadata.py`.
*   **Logic**:
    *   Read `portfolio_candidates.json` (Run-specific).
    *   Read Global Catalogs (Lakehouse).
    *   Join attributes (Sector, Lot Size, Tick Size) to candidates.
    *   **NO External Calls**.

## 4. Migration Plan

### 4.1 Makefile Updates
*   Create `make meta-ingest`: Runs both `build_metadata_catalog` and `fetch_execution_metadata`.
*   Update `make flow-data`: Include `meta-ingest` after `data-ingest`.

### 4.2 Pipeline Updates
*   `run_production_pipeline.py`: Replace `make meta-refresh` with `scripts/enrich_candidates_metadata.py`.

## 5. Verification
*   Run `flow-data`. Verify catalogs are updated.
*   Run `flow-production`. Verify it does *not* hit TradingView/CCXT endpoints.
