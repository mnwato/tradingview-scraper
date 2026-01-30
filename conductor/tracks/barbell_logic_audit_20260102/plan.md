# Plan: Barbell Optimizer Logic Audit

## Phase 1: Diagnostics
- [x] **Task**: Inspect `data/lakehouse/portfolio_optimized_v2.json` to see which symbols were selected for the BARBELL profile.
- [x] **Task**: Cross-reference selected symbols with `data/lakehouse/portfolio_clusters.json`.
- [x] **Task**: Add debug logging to `scripts/optimize_clustered_v2.py` during the aggressor selection phase.

## Phase 2: Code Fixes
- [x] **Task**: Refactor `BarbellEngine` selection logic to strictly enforce cluster uniqueness.
- [x] **Task**: Implement a fallback mechanism if high-alpha candidates are too concentrated in a single cluster.

## Phase 3: Validation
- [x] **Task**: Rerun `make daily-run` and verify that the logic audit passes for the BARBELL profile.
- [ ] **Task**: Document findings in `REPORT.md`.
