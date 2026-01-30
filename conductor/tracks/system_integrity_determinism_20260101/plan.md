# Plan: System Integrity, Replayability & Determinism (SIRD)

## Phase 1: Deterministic Discovery & Local Replay
- [ ] Task: Implement Discovery Snapshotting logic.
    - [ ] Sub-task: Update `Screener.screen` to save raw JSON responses to `artifacts/discovery/`.
    - [ ] Sub-task: Ensure the `run_id` is embedded in the snapshot metadata.
- [ ] Task: Create the `DiscoveryReplayer` utility.
    - [ ] Sub-task: Add `--replay-from <run_id>` support to `scripts/build_metadata_catalog.py` and `scripts/run_production_pipeline.py`.
    - [ ] Sub-task: Implement logic to bypass TradingView API and load symbols/rankings from the local snapshot.
- [ ] Task: Update the Audit Genesis Block.
    - [ ] Sub-task: Log the initial candidate pool (symbols + rank) into `audit.jsonl`.
- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Remote Artifact Persistence (HuggingFace/LFS)
- [ ] Task: Implement `ArtifactOrchestrator` for cloud storage.
    - [ ] Sub-task: Integrate `huggingface_hub` for pushing/pulling binary artifacts.
    - [ ] Sub-task: Implement Git LFS fallback for large Parquet files.
- [ ] Task: Link Ledger to Remote Refs.
    - [ ] Sub-task: Update `AuditLedger.record_outcome` to include `remote_url` and `content_hash`.
    - [ ] Sub-task: Test end-to-end "Context Recovery" (Download artifacts from HF based on an `audit.jsonl` entry).
- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: Selection Deep-Trace & Solver Determinism
- [ ] Task: Refactor `SelectionEngineV3` for mathematical traceability.
    - [ ] Sub-task: Capture and return internal probability matrices (MPS) and predictability scores (PE, Hurst, ER).
    - [ ] Sub-task: Update `run_selection` to log these deep-contexts into the ledger `outcome.data`.
- [ ] Task: Enforce Optimizer Determinism.
    - [ ] Sub-task: Standardize `random_state` seeds across `skfolio`, `scikit-learn`, and `cvxpy`.
    - [ ] Sub-task: Implement `WeightParityAuditor` to compare weight vectors between original and replayed runs.
- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

## Phase 4: Final Replay Validation
- [ ] Task: Execute the "Bit-Identical Replay" test.
    - [ ] Sub-task: Run a 2025 window, push artifacts, and verify the `audit.jsonl`.
    - [ ] Sub-task: Replay the same window using `--replay-from` and cloud artifacts.
    - [ ] Sub-task: Assert that `WeightParityAuditor` reports 0.00% difference.
- [ ] Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)
