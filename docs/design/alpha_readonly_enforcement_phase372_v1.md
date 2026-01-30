# Design: Phase 372 Alpha Read-Only Enforcement (v1)

## 1. Purpose
Phase 372 makes the Alpha cycle safer by ensuring that “alpha/prep” scripts default to read-only behavior and do not accidentally trigger network ingestion.

This phase is based on the DataOps contract:
- DataOps mutates the lakehouse (network allowed).
- Alpha consumes the lakehouse as read-only (network forbidden).

Reference: `docs/specs/dataops_architecture_v1.md`.

## 2. Scope
This phase focuses on the most dangerous entrypoint: `scripts/prepare_portfolio_data.py`.

## 3. Design

### 3.1 Default to Lakehouse-Only
`scripts/prepare_portfolio_data.py` MUST default to `PORTFOLIO_DATA_SOURCE=lakehouse_only`.

### 3.2 Fail Fast on Network Mode
If the user explicitly sets `PORTFOLIO_DATA_SOURCE` to a non-lakehouse value:
- the script MUST raise a clear error explaining that ingestion belongs to DataOps,
- and MUST point the operator to `make flow-data`.

Rationale:
- The current script references a `DataPipelineOrchestrator` module that is not present; even if it existed, this would be the wrong layer for network ingestion.

### 3.3 Strict Isolation
When `TV_STRICT_ISOLATION=1`:
- any fallback to lakehouse candidate manifests must be denied unless the candidates file is already within the run directory.

## 4. Acceptance Criteria (TDD)
1. With no `PORTFOLIO_DATA_SOURCE` env var, the script runs in lakehouse-only mode.
2. With `PORTFOLIO_DATA_SOURCE=fetch`, the script fails fast with a deterministic message and does not attempt network imports.

