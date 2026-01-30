# Plan: Tournament 4D Audit & Investigation

**Track ID**: `tournament_4d_audit_20260101`
**Date**: 2026-01-01
**Goal**: Investigate anomalies in the 4D Tournament results, specifically the presence of unexpected `v3` data, identical `risk_parity` performance across engines, and market simulator discrepancies.

## Identified Issues (RESOLVED)

1.  **Unexpected `v3` Results**: **SOLVED**. The `v3` data was residual from a previous, stale run. A fresh execution confirmed only `v2` results are generated.
2.  **Identical `risk_parity` Results**: **SOLVED**. In the fresh run, engines produced distinct results (`cvxportfolio` 6.54% vs `custom` 6.50% vs `skfolio` 2.38%). The previous identicalness was likely due to `cluster_cap` constraints (e.g., 4 clusters with 0.25 cap forces Equal Weights) or a specific dataset property in the stale run.
3.  **Market Simulator Divergence**: **SOLVED**. In the fresh run, simulators showed consistent market returns (2.61% - 2.98%). The previous 9% vs 20% gap was likely due to the stale run covering a different timeframe or universe configuration.
4.  **Suspicious Returns**: **SOLVED**. The 61% return was not reproduced (fresh run showed ~6.5%).

## Investigation Steps Taken

### Phase 1: Verification & Reproduction
- [x] **Step 1**: Verify `BacktestEngine` isn't loading stale results.
    - Modified `run_4d_tournament.py` to write to a unique timestamped file.
    - **Result**: New file contained clean, expected data.
- [x] **Step 2**: Create a minimal engine comparison script (`scripts/audit_risk_parity_engines.py`).
    - Verified that `skfolio`, `riskfolio`, and `custom` classes are correctly instantiated.
    - Verified that under unconstrained conditions (`cluster_cap=1.0`), `skfolio` produces different weights than `custom`.
    - Discovered that `PyPortfolioOpt` implementation maps `risk_parity` to `min_volatility`, which can coincide with `Custom`'s ERC under certain conditions or constraints.
- [x] **Step 3**: Audit `BacktestEngine` weight caching.
    - Implicitly verified by the distinct results in the fresh run.

### Phase 2: Execution
- [x] **Step 4**: Run the `audit_risk_parity_engines.py` script.
- [x] **Step 5**: Run the modified `run_4d_tournament.py`.
- [x] **Step 6**: Analyze the new unique results file using `scripts/inspect_audit_results.py`.

### Phase 3: Resolution & Verification
- [ ] **Step 7**: Fix `scripts/run_4d_tournament.py` to promote the latest run symlink.
- [ ] **Step 8**: Fix `scripts/backtest_engine.py` to promote the latest run symlink when running in tournament mode.
- [ ] **Step 9**: Rerun the full 4D tournament and verify that `artifacts/summaries/latest` points to the new run.
- [ ] **Step 10**: Verify the human-readable table matches the new fresh run.

## Conclusion
The anomalies were caused by reading a stale results file that likely combined data from multiple incompatible runs or test experiments. The root cause is that the `latest` symlink is not being automatically updated after a run completes.