# Data Pipeline v2: Streamlined Ingestion & Auto-Healing

## 1. Overview
This document defines the architecture for the "Streamlined Data Pipeline" (Phase 173), aiming to eliminate manual intervention for stale data repair. The goal is to integrate discovery, validation, and targeted repair into a single, robust workflow.

## 2. Problem Statement
- **Reactive Repair**: Currently, stale data is detected *after* ingestion fails or via manual audit (`validate_portfolio_artifacts.py`).
- **Manual Toil**: Repair requires constructing a targeted JSON list and running a separate command (`make data-refresh-targeted`).
- **Pipeline Friction**: Production runs halt on "Health Audit" failures, requiring operator intervention.

## 3. Architecture: "Smart Ingestion" Loop

The proposed workflow replaces the linear `scan -> fetch -> audit` sequence with a feedback loop:

### 3.1 Components
1.  **Discovery (Scanner)**: Generates `portfolio_candidates_raw.json` (as is).
2.  **Lakehouse Auditor**: A lightweight pre-flight check that compares candidates against the Lakehouse.
    - **Input**: Candidate list.
    - **Logic**: Check file existence and freshness (< 24h for crypto).
    - **Output**: A list of `stale_candidates` and `missing_candidates`.
3.  **Smart Fetcher (`prepare_portfolio_data.py`)**:
    - **Mode A (Standard)**: Fetches missing data.
    - **Mode B (Targeted Repair)**: If `stale_candidates` exist, it automatically switches to `PORTFOLIO_FORCE_SYNC=1` for *only* those assets.
    - **Optimization**: Uses `RegistryManager` to lock and deduplicate fetches.

### 3.2 Workflow Logic
```mermaid
graph TD
    A[Start Pipeline] --> B[Discovery (Scan)]
    B --> C{Auditor Check}
    C -->|All Fresh| D[Aggregation]
    C -->|Stale/Missing Found| E[Smart Fetch (Targeted)]
    E --> C
    D --> F[Selection]
```

## 4. Implementation Plan

### 4.1 Tooling Enhancements (COMPLETED)
- **`prepare_portfolio_data.py`**:
    - [x] Standardized on **Physical Symbols** for data storage (`returns_matrix.parquet`).
    - [x] Removed logic/direction awareness from the Data Layer.
    - [ ] Add `--smart-repair` flag.
    - [ ] Integrate `PortfolioAuditor` logic to detect staleness *before* attempting fetch.
    - [ ] Internally construct the "Targeted List" from the audit result.
    - [ ] Execute a 2-pass fetch:
        1.  **Pass 1**: Standard fetch for missing assets.
        2.  **Pass 2**: Force-sync fetch for stale assets (if any).

### 4.2 Orchestration (COMPLETED)
- **`run_production_pipeline.py`**:
    - [x] Injected `Strategy Synthesis` (Step 9) to re-couple Logic Atoms just-in-time for Optimization.
    - [ ] Update `Aggregation` step to use the `--smart-repair` flag.
    - [ ] This effectively merges "High-Integrity Preparation" and "Health Audit" recovery into the data prep phase.

### 4.3 Validation
- The `Health Audit` step remains as a **Hard Gate**, but it should pass on the first try due to the upstream smart repair.

## 5. Migration Strategy
1.  **Phase 1**: Update `prepare_portfolio_data.py` to support internal self-audit.
2.  **Phase 2**: Update `Makefile` and `run_production_pipeline.py` to utilize the new capability.
3.  **Phase 3**: Deprecate manual `data-refresh-targeted` workflow in favor of the automated loop.
