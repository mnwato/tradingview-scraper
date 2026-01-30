# Market Profile Unification & Validation (Jan 2026)

This document details the transition from a standalone `market` engine to a unified `market` profile supported by all optimization engines.

## 1. Architectural Shift

Previously, the institutional benchmark was handled by a special-case `MarketBaselineEngine`. This created duplication in rebalancing and backtesting logic.

**New Standard**: The institutional benchmark is now a native `market` profile implemented in the base optimization class (`CustomClusteredEngine`). Baseline taxonomy is standardized in `docs/specs/optimization_engine_v2.md`.

| Feature | Legacy Implementation | Unified Implementation |
| :--- | :--- | :--- |
| **Engine Class** | `MarketBaselineEngine` | Integrated into all engines |
| **Profile Name** | `market_baseline` / `equal_weight` (legacy) | `market` |
| **Universe** | Fixed SPY (hardcoded fallback) | `settings.benchmark_symbols` |
| **Parity** | Engine-specific | Guaranteed across all engines |

Note: `equal_weight` remains a distinct hierarchical equal-weight profile (see `docs/specs/optimization_engine_v2.md`) and is not a market baseline.

## 2. Implementation Details

The `market` profile logic follows these steps:
1.  **Symbol Filtering**: Filter the available training returns to only those found in `settings.benchmark_symbols`.
2.  **No Fallback**: If no benchmark symbols are found, the engine returns empty weights with a warning.
3.  **Equal Weighting**: Assign $1/N$ weight to all target symbols.
4.  **Metadata Tagging**: All benchmark assets are tagged with `Cluster_ID: MARKET`.

## 3. Validation

### A. Unit Testing
The implementation was validated using `tests/test_market_profile.py`:
- **`test_market_profile_parity`**: Confirmed that `custom`, `skfolio`, `riskfolio`, and `cvxportfolio` produce bit-identical weights for the `market` profile.
- **`test_multi_asset_market_profile`**: Validated that multi-asset benchmarks (e.g., SPY + QQQ) are correctly equal-weighted.
- **`test_market_profile_fallback`**: Verified graceful fallback behavior when benchmark data is missing.

### B. Integration Testing
A tournament run was executed comparing all engines using the `market` profile.
- **Result**: All simulators reported identical returns and turnover for the benchmark, confirming the elimination of "Simulator Bias" for the control group.

## 4. Conclusion
The unified `market` profile simplifies the codebase while providing a more robust and transparent mechanism for simulator calibration and institutional benchmarking.

### Summary Table

| Category | Profile Name | Definition |
| :--- | :--- | :--- |
| **Institutional** | `market` | EW over Benchmark Symbols (SPY). Noise-free hurdle. |
| **Research** | `benchmark` | EW over Selected Winners. Risk-profile comparator. |
| **Diagnostics** | `raw_pool_ew` | EW over Raw Pool (Excl. Benchmarks). Selection Alpha isolate. |
