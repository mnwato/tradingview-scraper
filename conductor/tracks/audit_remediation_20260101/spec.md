# Specification: Audit Remediation 2026-01-01

## 1. Overview
This track addresses maintenance items identified during the Comprehensive Audit on 2026-01-01. The goal is to standardize metadata, robustly resolve symbol duplicates using SCD Type 2 logic, and analyze coverage gaps using existing tooling.

## 2. Functional Requirements

### 2.1 Metadata Standardization (Scripted)
- **Target Script:** `scripts/cleanup_metadata_catalog.py`
- **Action:** Update the script to specifically check for and insert `FOREX` exchange metadata into the `ExchangeCatalog` if missing.
    -   **Metadata:** `FOREX`: timezone=`America/New_York`, is_crypto=`False`, country=`Global` (or specific if known).

### 2.2 SCD Type 2 Catalog Cleanup (Scripted)
- **Target Script:** `scripts/cleanup_metadata_catalog.py`
- **Logic Enhancement:** Refine the duplicate removal logic.
    -   Identify symbols with multiple records.
    -   Sort by `updated_at`.
    -   Ensure only the most recent record is "active" (`valid_until` is None).
    -   Explicitly set `valid_until` on all older records to the `updated_at` (or `valid_from`) of the next record in the sequence, ensuring a continuous history without overlap.

### 2.3 Coverage Gap Analysis
- **Target Script:** `scripts/comprehensive_audit.py` (and potentially `scripts/check_catalog_stats.py`)
- **Action:**
    -   Run the audit to get the exact list of missing symbols/types.
    -   Analyze why the coverage score is 50/100 (likely due to missing types like Options, Bonds, or specific exchange coverage).
    -   Generate a report: `docs/research/coverage_gap_analysis_2026.md`.

## 3. Non-Functional Requirements
- **Idempotency:** The cleanup script must be safe to run multiple times without corrupting history.
- **Data Integrity:** `FOREX` metadata addition must not overwrite existing valid metadata if present (use upsert with care).

## 4. Acceptance Criteria
- `scripts/cleanup_metadata_catalog.py` runs successfully.
- `scripts/comprehensive_audit.py` reports:
    -   `FOREX` metadata is present and consistent.
    -   0 "active" duplicates for symbols (all duplicates have `valid_until` set).
    -   Data Quality Score remains 100/100.
- `docs/research/coverage_gap_analysis_2026.md` exists and explains the 50/100 coverage score.

## 5. Out of Scope
- Fetching new market data (only metadata cleanup).
- Refactoring `MetadataCatalog` internals beyond cleanup logic.
