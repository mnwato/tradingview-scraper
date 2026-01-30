# Specification: System Integrity, Replayability & Determinism (SIRD)

## 1. Overview
This track formalizes the "Truth Chain" of the quantitative pipeline. It ensures that any production result can be perfectly replayed, audited, and traced back to its raw inputs. By combining cryptographic ledgering with artifact snapshotting (HuggingFace/LFS), we eliminate temporal "API noise" and ensure bit-identical reproducibility.

## 2. Functional Requirements

### 2.1 Deterministic Discovery (The "Lock" Standard)
- **Snapshotting**: Every discovery run must save the raw TradingView API response as a timestamped JSON artifact in `artifacts/discovery/`.
- **Candidate Locking**: The exact candidate pool (symbols + ranks) must be logged into the `audit.jsonl` genesis block for that run.
- **Replay Mode**: Implement a `--replay-from <run_id>` flag that bypasses the live API and loads the discovery snapshot.

### 2.2 Replayability via Remote Artifacts
- **Cloud Provenance**: Integrate a mechanism to push run-critical artifacts (Discovery Snapshots, Returns Matrices, Pruned Universes) to **HuggingFace Hub** or **Git LFS**.
- **Ref-Linkage**: The `audit.jsonl` must include the remote reference (URL/Hash) to these artifacts, ensuring the "context" is never lost even if local `data/` is cleared.

### 2.3 Selection & Engine Traceability
- **Deep Trail Logging**: Refactor `SelectionEngineV3` to log the full mathematical context (Individual MPS probabilities, PE/Hurst scores per asset) into the `outcome.data` field of the ledger.
- **Solver Determinism**: Standardize seeds for all optimizers (`scipy`, `cvxpy`, `skfolio`) and log the solver status/iterations to detect non-deterministic numerical drift.

### 2.4 Metadata & Pipeline Persistence
- **State Serialization**: Save the exact `SelectorConfig` and `FeatureFlags` state at the moment of execution to the run directory.
- **Metadata PIT Audit**: Ensure that any metadata "Correction" (like the FOREX TZ fix) is recorded as a versioned change in the decision chain.

## 3. Non-Functional Requirements
- **Bit-Identicality**: Replaying a backtest window with the same artifacts MUST result in identical weights and realized returns.
- **Auditable Pedigree**: Every CSV/MD report must be linkable to a specific `run_id` and `audit_hash`.

## 4. Acceptance Criteria
- Successful 100% bit-identical replay of a 2025 tournament window using `--replay-from`.
- `audit.jsonl` contains detailed veto reasons and predictability metrics for all candidates.
- Integration prototype for HuggingFace/LFS artifact pushing is operational.

## 5. Out of Scope
- Migrating the entire historical lakehouse to LFS (only new runs and critical research snapshots).
- Real-time execution determinism (focus on research/backtest pipeline).
