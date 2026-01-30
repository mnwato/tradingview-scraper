# Specification: Audit Ledger 2.0 - Transparency & Replayability (Jan 2026)

This document defines the standards for institutional-grade auditable transparency within the TradingView Scraper quantitative framework.

## 1. Requirements

To meet MiFID II and SEC regulatory expectations for algorithmic trading, the audit ledger must support the following:

| Requirement | Implementation | Rationale |
| :--- | :--- | :--- |
| **Integrity** | SHA-256 Hash Chaining | Prevents tampering with historical records. |
| **Reproducibility** | Parameter Persistence | Every input (train window, lambda, gamma) must be recorded. |
| **Replayability** | Deterministic Replay Tool | Ability to rerun a specific window from a ledger entry. |
| **Lineage** | Data Hashing | Verifies that the input data at T=0 matches the data during reconstruction. |
| **Provenance** | Environment Metadata | Record library versions (`uv.lock`) and Git commit hash. |

## 2. Technical Design

### A. Record Schema Expansion
The `Action` record in the ledger will be expanded to include:
- `env_hash`: Hash of the `uv.lock` and project configuration.
- `data_slice_hash`: Hash of the specific training window slice used.
- `state_seed`: The random seed used for any stochastic optimizers.
- `context`: Structured metadata required for deterministic replay, including:
  - `selection_mode`, `rebalance_mode`
  - `train_window`, `test_window`, `step_size`
  - `window_index`, `train_start`, `test_start`, `test_end`
  - `engine`, `profile`, `simulator`
  - `universe_source` (raw pool: `canonical` vs `selected`)

### B. Replay Orchestrator
A new tool, `scripts/replay_backtest.py`, will be developed to:
1.  Parse a specific `hash` from the audit ledger.
2.  Restore the `params` recorded in the `intent` block.
3.  Locate the historical data (matching the `input_hashes`).
4.  Execute the step and verify the `outcome_hash`.

## 3. Implementation Status (Jan 2026)

1.  **Enhance `AuditLedger` Class**: **COMPLETED**. Integrated `get_env_hash()` and `git_hash` into the Genesis block.
2.  **Robust Data Hashing**: **COMPLETED**. Implemented ultra-stable `get_df_hash` that forces naive UTC indexing for deterministic replay parity across environments.
3.  **Cluster Lineage Verification**: **COMPLETED**. Optimization intents now record the hash of the hierarchical cluster state, preventing mismatched tree reconstructions during replay.
4.  **Develop Replay CLI**: **PROTOTYPED**. Verified the ability to reconstruct window parameters and verify data lineage.

## 4. Institutional Standards Compliance
The system now adheres to the following standards:
- **Authenticity**: Every run starts with a genesis block pinning the Git commit and library environment.
- **Integrity**: Each record is linked via SHA-256 to its predecessor, preventing un-traceable modifications.
- **Reconstructibility**: Decisions are recorded with full parameter sets, allowing for point-in-time forensic analysis.

## 5. Tournament Linkage (Current Behavior)
When `feat_audit_ledger` is enabled:
- `backtest_optimize` intents capture training data hashes and cluster lineage hashes.
- `backtest_simulate` outcomes capture test return hashes and key metrics (e.g., Sharpe).

Notes:
- The ledger is written to the run-scoped `artifacts/summaries/runs/<RUN_ID>/audit.jsonl`.
- Derived reports (e.g., `full_4d_comparison_table.md`) are generated from tournament outputs and are not separately hashed in the ledger unless explicitly recorded by a writer.

### 5.1 Required Backtest Context (Jan 2026)
For every `backtest_optimize` and `backtest_simulate` entry, the ledger must also include a `context` block with:
- `selection_mode`, `rebalance_mode`
- `train_window`, `test_window`, `step_size`
- `window_index`, `train_start`, `test_start`, `test_end`
- `engine`, `profile`, `simulator`
- `universe_source` (raw pool baseline: `canonical` or `selected`)
