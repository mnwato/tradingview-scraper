# Binance Ratings Meta-Portfolio Rerun Status (2026-01-18)

## 1. Execution Summary
**Date**: 2026-01-18  
**Objective**: Full-spectrum production rerun of Binance Rating-Based Meta-Portfolios.
**Standard**: Crypto Sleeve Requirements v3.6.4 (Bi-Weekly 10-day alignment).

## 2. Target Profiles

### 2.1 Atomic Sleeves (Pillar 2)
| Profile | Direction | Status | Run ID |
| :--- | :--- | :--- | :--- |
| `binance_spot_rating_all_long` | LONG | ✅ COMPLETE | `20260118-161253` |
| `binance_spot_rating_all_short` | SHORT | ✅ COMPLETE | `20260118-161504` |
| `binance_spot_rating_ma_long` | LONG | ✅ COMPLETE | `20260118-161655` |
| `binance_spot_rating_ma_short` | SHORT | ✅ COMPLETE | `20260118-161849` |

### 2.2 Meta-Portfolios (Pillar 3)
| Meta Profile | Sleeves | Status |
| :--- | :--- | :--- |
| `meta_benchmark` | All Long + All Short | ✅ COMPLETE |
| `meta_ma_benchmark` | MA Long + MA Short | ✅ COMPLETE |

## 3. Pipeline Stages
- [x] **DataOps**: `make flow-data` (Scans, Ingests, Meta, Features).
- [x] **Discovery**: Execute scanners for all rating-based strategies.
- [x] **Sleeve Execution**: Parallel execution of the 4 atomic production pipelines.
- [x] **Meta-Aggregation**: Recursive return aggregation for `meta_benchmark` and `meta_ma_benchmark`.
- [x] **Optimization**: Hierarchical Risk Parity (HRP) allocation at the meta-level.
- [x] **Flattening**: Collapse meta-weights to physical Binance Spot symbols.
- [x] **Certification**: Generate forensic audit reports.

## 5. Forensic Audit Findings (Phase 221)
- **Solver Integrity**: 100% failure rate for `skfolio` and `riskfolio` engines due to missing environment dependencies.
    - *Impact*: Sleeves were marked as **DEGRADED** in meta-reports as they failed to generate all 8 risk profiles.
    - *Action*: Native `custom` and `cvxportfolio` engines successfully provided baseline coverage (`hrp`, `min_variance`, `max_sharpe`, `barbell`).
- **Winner pool Stability**: SSP (Selection Scarcity Protocol) maintained $N \ge 3$ in 98% of windows.
    - Only 2 windows in `long_all` triggered extreme sparsity (n < 3), handled gracefully by fallbacks.
- **Metric Sanity**: 0% "Extreme Metric" anomalies detected. 
    - Wealth persistence and bankruptcy floor logic verified as stable across all 4 runs.
    - realized Sharp ratios remained in the [0.2, 1.2] range at the sleeve level.

## 6. Proposed Streamlining Tasks
1. [ ] **Environment Hardening**: Integrate `skfolio` and `riskfolio` into the `uv` lockfile or prune them from `production` manifest to reduce log noise.
2. [ ] **Meta-Aggregation Cache**: Implement `.cache/` directory for `build_meta_returns.py` to prevent redundant recursive loads in large fractal trees.
3. [ ] **Anomaly Guardrail**: Add a `scripts/validate_meta_audit.py` step to the pipeline that fails if any sleeve has > 25% solver failures.
4. [ ] **Dynamic Weight Flattening**: Optimize `flatten_meta_weights.py` to handle 100+ nested sleeves without memory bloat.
