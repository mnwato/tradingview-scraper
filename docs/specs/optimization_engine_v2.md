# Optimization Engine V2: Profile-Centric Allocation

The Profile-Centric Optimization Engine (v2) is an institutional-grade framework designed to handle venue redundancy and benchmark library-specific solver variance across disparate asset classes. This document is the single source of truth for profile definitions, baseline taxonomy, and universe semantics.

## 1. Universe Definitions (Canonical vs Natural-Selected)

### Canonical Universe (Raw Pool)
- **Source**: `data/lakehouse/portfolio_candidates_raw.json`
- **Definition**: The merged, post-discovery universe prior to any selection or pruning.
- **Requirement**: All natural-selected universes must be strict subsets of the canonical universe.
- **Canonical returns**: `data/lakehouse/portfolio_returns_raw.pkl` built by running `scripts/prepare_portfolio_data.py` with `CANDIDATES_FILE=portfolio_candidates_raw.json` and `PORTFOLIO_RETURNS_PATH=portfolio_returns_raw.pkl`.
  - **Pipeline**: Generated during `make data-prep-raw` alongside raw candidate aggregation.

### Natural-Selected Universe (Selection Winners)
- **Source**: `data/lakehouse/portfolio_candidates.json`
- **Definition**: The selection-engine winners layered on top of the canonical universe.
- **Default**: The production returns matrix (`data/lakehouse/portfolio_returns.pkl`) is built from this manifest by `scripts/prepare_portfolio_data.py`.

### Design Implication
- **Selection alpha isolation** requires a canonical baseline (`raw_pool_ew`) that is not affected by selection-mode sweeps.
- **Optimization profiles** operate on the active universe passed into the engine (typically natural-selected unless explicitly overridden).
- **Metadata prerequisite**: Candidate manifests must contain `tick_size`, `lot_size`, and `price_precision` before any selection/tournament run.
- **Automated Gate**: `scripts/metadata_coverage_guardrail.py` enforces a ≥95% coverage threshold as a mandatory pipeline gate.
- **Vetoes**: Driven by the **candidate manifests** (not `portfolio_meta*.json`), so enrichment must occur after each manifest refresh.

## 2. Baseline Profiles Standard (Single Source of Truth)

### Standard Taxonomy (Supported Profiles)

| Category | Profile Name | Description |
| :--- | :--- | :--- |
| **Baseline** | `market` | EW over Benchmark Symbols (e.g., SPY). |
| **Baseline** | `benchmark` | EW over all Natural-Selected Winners. |
| **Risk Profile**| `min_variance` | Optimized Defensive Sleeve. |
| **Risk Profile**| `max_sharpe` | Optimized Growth Sleeve. |
| **Risk Profile**| `hrp` | Hierarchical Risk Parity. |
| **Strategy** | `barbell` | Combined Core + Aggressor Sleeves. |
| **Diagnostic** | `raw_pool_ew` | EW over the Raw Pool (excluding benchmarks). |

Only the official profiles listed above are supported. Legacy labels (e.g., `market_baseline`, `benchmark_baseline`, `equal_weight` as a baseline) have been decommissioned.

Note: `equal_weight` may still appear in backtest outputs under the baseline engine for comparison, but it remains a risk profile (see table below).

### 2.1 `market` (Institutional Baseline)
- **Universe**: `settings.benchmark_symbols` present in the returns matrix.
- **Weighting**: Equal-weight across benchmark symbols.
- **Constraints**: Long-only, sum to 1.
- **Audit**: Record benchmark symbols, symbol count, and returns hash in `audit.jsonl`.
- **Current behavior**: If no benchmark symbols are present, the engine returns empty weights with a warning.
- **Design requirement**: No fallback. Missing benchmarks must return empty weights with a warning.
- **Usage**: Simulator calibration and institutional hurdle rate, not a proxy for the active universe.

### 2.2 `benchmark` (Research Baseline)
- **Universe**: Active universe passed into the engine (typically the natural-selected universe).
- **Weighting**: Asset-level equal weight (no clustering, no optimizer).
- **Constraints**: Long-only, sum to 1.
- **Audit**: Record universe source, symbol count, and returns hash.
- **Purpose**: Baseline for comparing **risk profiles** while holding selection fixed; default comparator in backtests.

### 2.3 `raw_pool_ew` (Selection-Alpha Baseline, Backtest-only)
- **Status**: Not an optimization profile; generated in `scripts/backtest_engine.py`.
- **Universe**: Controlled by `TV_RAW_POOL_UNIVERSE=selected|canonical` (or `RAW_POOL_UNIVERSE` when promoted by the pipeline).
- **Canonical returns path**: `RAW_POOL_RETURNS_PATH` / `TV_RAW_POOL_RETURNS_PATH` (defaults to `data/lakehouse/portfolio_returns_raw.pkl`).
- **Weighting**: Asset-level equal weight across valid raw-pool symbols, excluding `benchmark_symbols`.
- **Invariance requirement**: Must be selection-mode invariant when the universe source is unchanged.
- **Invariance protocol**: Validate invariance by running *the same universe source* (canonical or selected) across different selection modes. Do **not** compare canonical vs selected as an invariance test (they are different universes by definition).
- **Coverage requirement**: Canonical returns must contain at least one contiguous window of `train + test + 1` rows. If canonical history starts later than the selected-returns index, `raw_pool_ew` will yield **0 windows** unless the tournament `start_date` is shifted to the canonical start (or windows are shortened).
- **Stability gate**: Treat `raw_pool_ew` as **selection benchmark baseline** per universe once window coverage is complete and invariance holds. If either fails, mark as **diagnostic only** and exclude from baseline comparisons.
- **Comparator scope**: Use `raw_pool_ew` only for **selection alpha** diagnostics; use `benchmark` for risk profile comparisons. Selection alpha requires **canonical raw_pool_ew** vs **selected benchmark** (otherwise $A_s$ collapses toward zero by construction).

## 3. Risk Profile Comparison Table (All Supported Profiles)

| Profile | Category | Universe | Weighting / Optimization | Hierarchy / HERC | Intended use & audit |
| --- | --- | --- | --- | --- | --- |
| `market` | Baseline | Benchmark symbols | Equal-weight across benchmark symbols | None | Simulator parity; audit benchmark symbols + hash |
| `benchmark` | Baseline | Active (natural-selected) universe | Asset-level equal weight | None | Optimization-alpha baseline; audit universe source + count |
| `raw_pool_ew` | Baseline (backtest) | Canonical or selected (via `TV_RAW_POOL_UNIVERSE`) | Asset-level equal weight; excludes benchmarks | None | Selection-alpha diagnostic; only baseline if stable + invariant |
| `equal_weight` | Risk | Active universe | Cluster-level equal weight | HERC 2.0 intra (inverse variance) | Neutral diversified profile |
| `min_variance` | Risk | Active universe | Cluster-level minimum variance | HERC 2.0 intra | Defensive risk control |
| `hrp` | Risk | Active universe | Cluster-level HRP (native per engine) | HERC 2.0 intra | Structural risk parity |
| `risk_parity` | Risk | Active universe | Cluster-level equal risk contribution | HERC 2.0 intra | Turbulent/CRISIS defense |
| `max_sharpe` | Risk | Active universe | Cluster-level max Sharpe / mean-variance | HERC 2.0 intra | Growth regime focus |
| `barbell` | Strategy | Active universe | Aggressor sleeve + core HRP | HERC 2.0 intra (core) | Convexity + capital preservation. **Requires explicit aggressor forcing** in the optimizer, as the V3 Selection Engine naturally prunes high-volatility assets (like `AGQ` or `ASTX`) in favor of stable anchors (`SLV`). |
| `adaptive` | Meta | Active universe | Switches profile by market environment | HERC 2.0 per chosen profile | **Mappings**: TURBULENT -> `hrp`, QUIET/NORMAL -> `max_sharpe`. |

Notes:
- For cluster-based profiles, intra-cluster weights are produced by **HERC 2.0** (inverse variance) in the Custom engine and are applied downstream when expanding cluster weights to asset weights.
- `equal_weight` is **Hierarchical Equal Weight** (cluster-level equal weight with HERC intra), not a flat asset-level EW.
- `barbell` is cluster-driven: select the top `max_aggressor_clusters` clusters by `Antifragility_Score` (currently 1 leader per cluster), allocate the aggressor sleeve via `aggressor_weight`, and allocate the core sleeve via `hrp` over the remaining clusters. When `aggressor_weight` is left at its default, it is regime-adjusted: QUIET 15% / NORMAL 10% / TURBULENT 8% / CRISIS 5%.

## 4. Profile-Centric Architecture (Jan 2026)

As of the 4D Tournament Meta-Analysis, the framework uses a **Profile-First** model. Universal fallbacks are removed so that every backend library (`skfolio`, `riskfolio`, etc.) uses its native solvers for each risk paradigm.

### Layer 1: Across Clusters (Factor Level)
The total capital is first distributed across high-level hierarchical risk buckets.
- **Max Cluster Cap (25%)**: Enforced via linear constraints ($w_{cluster} \le 0.25$).
- **Numerical Stability**: Standardized on **Tikhonov Regularization** ($10^{-6} \cdot I$).
- **Turnover Control**: L1 penalty on weight changes vs prior state.

### Layer 2: Within Clusters (Instrument Level)
- **HERC 2.0**: Intra-cluster weights use inverse variance to equalize risk contribution.
- **Cluster Benchmarks**: Cluster returns are computed as the risk-weighted (HERC) average of member assets.

## 5. Simulator Parity & Fidelity
All profiles are validated across synchronized simulators:
- **`cvxportfolio`**: High-fidelity standard (linear costs + N+1 alignment).
- **`nautilus` / `custom`**: Turnover-aware friction parity.
- **`vectorbt`**: Vectorized rapid prototyping.

## 6. Decision Support & Audit Trace
- **Audit Ledger**: Every decision is cryptographically logged in `audit.jsonl`.
- **Atomic Renaming**: Ensures audit logs remain uncorrupted during multi-threaded runs.
- **Selection Provenance**: Each run archives its specific selection state.

## 7. Current Status & Gaps (2026-01-03)
- **raw_pool_ew selection baseline**: Verified invariant across selection modes for same-universe runs (canonical v3/v3.2 and selected v3/v3.2). Guardrail automation remains open.
- **Canonical returns wiring**: `BacktestEngine` uses `portfolio_returns_raw.pkl` when present; `make data-prep-raw` generates canonical returns, but gap repair may still be required for full coverage.
- **Canonical window constraint**: If canonical returns start after the selected index, no walk-forward window can satisfy `train + test + 1` coverage (example: run `20260103-160121` produced 0 windows). Use a canonical-aligned `start_date` or shorter windows to validate baselines.
- **Audit completeness**: `raw_pool_symbol_count` and `raw_pool_returns_hash` are logged when `raw_pool_ew` windows exist; missing windows yield no audit entries.
- **Market fallback**: The `market` profile returns empty weights if benchmark symbols are missing (no fallback by design).
- **PyPortfolioOpt**: `max_sharpe` emits a warning when used with L2 regularization due to objective transformation.
- **Riskfolio HRP**: Flagged as "Experimental" due to a -0.95 correlation with standard HRP implementations in certain regimes.
- **Adaptive mapping**: `AdaptiveMetaEngine` currently maps `NORMAL` to `max_sharpe` (not `benchmark`).
