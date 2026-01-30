## 6. Audit & Reproducibility
- [x] **Immutable Ledger:** Implemented `audit.jsonl` with SHA-256 chaining.
- [x] **Data Lineage:** Implemented deterministic `df_hash` for return matrices.
- [x] **Audit Orchestration:** Wrapped pipeline steps in WAL (Write-Ahead Logging) blocks.
- [x] **Verification Tool:** Created `scripts/verify_ledger.py` for integrity audits.

## 7. High-Fidelity Backtesting
- [x] **PIT Risk Auditing**: Integrated `AntifragilityAuditor` into walk-forward training windows.
- [x] **State Persistence**: Holdings propagation between test windows for friction continuity.
- [x] **Universal Baseline**: Added Equal-Weighted universe engine for benchmark consistency.
