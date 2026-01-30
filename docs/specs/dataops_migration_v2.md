# DataOps v2 Migration Plan

## 1. Overview
This document outlines the migration of legacy data pipelines (Scanning, Ingestion, Meta-Enrichment) to the new **Lakehouse Architecture** using `flow-data`.

## 2. Legacy vs. Modern Workflow

| Feature | Legacy (`data-fetch`) | Modern (`flow-data`) |
| :--- | :--- | :--- |
| **Trigger** | Profile-based, inside `run_production_pipeline.py`. | Centralized `make flow-data` (Daily Cron). |
| **Ingestion** | `prepare_portfolio_data.py` (Ad-hoc API calls). | `ingest_data.py` (Idempotent Service). |
| **Metadata** | `meta-refresh` (Ad-hoc API calls). | `meta-ingest` (Centralized Catalog). |
| **Features** | None. | `feature-ingest` (TradingView Technicals). |
| **Storage** | Run-specific artifacts. | Centralized Lakehouse (Parquet) -> Run Snapshot. |

## 3. Migration Steps

### 3.1 Profile Updates
*   **Audit**: Verify all active profiles in `manifest.json`.
*   **Action**: Ensure `discovery` sections are correct, as `flow-data` uses them to generate candidates.

### 3.2 Scheduler Setup
*   **Cron**: Configure `0 0 * * * make flow-data` to keep the Lakehouse fresh.
*   **Gap Repair**: Configure `0 12 * * 0 make data-repair` (Weekly).

### 3.3 Orchestration Update
*   **Action**: `run_production_pipeline.py` is already updated to `lakehouse_only` mode.
*   **Validation**: Verify that running `flow-production` WITHOUT running `flow-data` first correctly fails/warns (or uses stale data if allowed).

## 4. Verification Plan (Phase 206)
1.  **Clean Slate**: Wipe `data/lakehouse`.
2.  **Full Cycle**: Run `make flow-data`.
    *   Verify `export/` has candidates.
    *   Verify `data/lakehouse/` has Parquet files.
    *   Verify `data/lakehouse/features/` has technicals.
3.  **Production Run**: Run `make flow-production`.
    *   Verify it runs without network I/O (check logs).
