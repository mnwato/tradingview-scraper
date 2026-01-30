# Specification: Grand Validation Tournament 2026

## 1. Overview
This track executes a definitive 4D validation tournament to confirm the current system's performance, stability, and integrity. It serves as the "Grand Audit" for the 2026 quantitative stack, comparing historical modes (v2) against modern multiplicative selection (v3/v3.1) with and without the new spectral predictability filters.

## 2. Functional Requirements

### 2.1 Multi-Dimensional Backtesting (The "Grand Matrix")
- **Selection Axis**: 
    - `v2`
    - `v3` (Baseline)
    - `v3_spectral` (Flags: `predictability_vetoes=1`, `efficiency_scoring=1`)
    - `v3.1` (Baseline)
    - `v3.1_spectral` (Flags: `predictability_vetoes=1`, `efficiency_scoring=1`)
- **Engine Axis**: `custom`, `skfolio`, `cvxportfolio`.
- **Profile Axis**: `risk_parity`, `hrp`, `benchmark`, `equal_weight`, `raw_pool_ew`.
- **Simulator Axis**: `custom`, `cvxportfolio`, `nautilus`.

### 2.2 Execution Parameters (Audited)
- **Period**: 2025-01-01 to 2025-12-31.
- **Protocol**: Continuous Walk-Forward (100% Coverage).
- **Train/Test/Step**: 126 / 21 / 21.
- **Rebalance Mode**: **Window-based** (`feat_rebalance_mode: "window"`). 
- **Costs**: 5bps slippage, 1bp commission.

### 2.3 Reporting, Data Review & Outlier Auditing
- **Main Table**: `grand_validation_4d_comparison.md` (Generated via `scripts/generate_human_table.py`).
- **Alpha Audit**: `selection_alpha_report.md` comparing Pruned vs. Raw Pool expectancy.
- **Risk Audit**: `risk_profile_report.md` verifying Vol/MDD realization parity across simulators.
- **Outlier Behavioral Audit**: `outlier_analysis_report.md` identifying permutations where results (Sharpe, MDD, Vol) deviate significantly (>2σ) from the group mean or baseline. Focuses on spotting:
    - **Simulator Drift**: Wide performance gaps between `nautilus` and `custom` for the same weights.
    - **Numerical Instability**: Extreme returns or drawdowns.
    - **Selection Artifacts**: Unexpected Raw Pool outperformance.
- **Integrity Audit**: Final cryptographic verification using `scripts/verify_ledger.py`.

## 3. Non-Functional Requirements
- **Decision Lineage**: Every configuration permutation must have a unique, traceable path in the `audit.jsonl`.
- **Reproducibility**: Environment pinning via `uv.lock` and Git SHA recording.

## 4. Acceptance Criteria
- All 150+ backtest permutations complete successfully.
- `audit.jsonl` verified with 0 breaks.
- Selection Alpha is positive for >70% of spectral-enabled runs.
- **Zero "Unexplained" Outliers**: Every 2σ deviation must be manually reviewed and justified in the report.

## 5. Out of Scope
- Real-time trading execution.
