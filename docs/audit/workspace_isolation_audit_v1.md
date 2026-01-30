# Audit: Workspace Isolation & Data Lineage (v1)

## 1. Objective
To evaluate the effectiveness of current workspace isolation mechanisms and identify gaps that could lead to data contamination or non-reproducible results in a distributed environment.

## 2. Identified Issues

### 2.1 Hardcoded Path Literals
- **Issue**: Numerous scripts and modules use `Path("data/...")` string literals instead of relying on `TradingViewScraperSettings`.
- **Risk**: Brittle execution in non-standard environments (like Ray workers) and difficulty in redirecting inputs/outputs for parallel testing.
- **Example**: `scripts/generate_portfolio_report.py`, `scripts/run_production_pipeline.py`.

### 2.2 Symbolic Link Snapshots
- **Issue**: `QuantSDK.create_snapshot` uses symlinks to provide "immutability".
- **Risk**: If the source file in `data/lakehouse` is mutated (e.g., by a concurrent DataOps run), the snapshot silently reflects the new data, violating MLOps immutability standards.
- **Remediation**: Use hard links or physical copies for small metadata files (JSON). Maintain symlinks only for large Parquet blobs.

### 2.3 Lakehouse Cross-Talk
- **Issue**: `consolidate_candidates.py` and `ingest_data.py` write directly to `data/lakehouse`.
- **Risk**: Multiple parallel discovery runs could overwrite `portfolio_candidates.json` simultaneously, leading to race conditions.
- **Remediation**: Write to run-specific `export` directories first, then perform a transactional commit to the Lakehouse.

### 2.4 Worker Environment Drift
- **Issue**: `SleeveActorImpl` initializes `TradingViewScraperSettings` independently.
- **Risk**: If the worker's working directory or environment variables differ from the host, settings resolution may diverge, leading to "Silent Path Mismatch".

## 3. Proposed Remediation (Phase 540)

1.  **Introduce `WorkspaceManager`**: A dedicated utility to manage the `data/` directory structure, handle symlinking/copying for snapshots, and provide absolute path resolution.
2.  **Strict Path Enforcement**: Conduct a final sweep to eliminate all `data/` string literals. Mandate that all core tools accept paths via CLI arguments or resolve them via the shared `settings` object.
3.  **Hybrid Snapshots**: Implement "Golden Snapshots" that copy JSON metadata and hard-link Parquet files to ensure true point-in-time isolation.
4.  **Transactional Ingestion**: Ensure DataOps tasks write to temporary buffers before updating the "Golden" Lakehouse state.

## 4. Conclusion
Current isolation is "ad-hoc". Moving to a formalized `WorkspaceManager` will harden the platform for large-scale distributed runs and ensure flawless data lineage.
