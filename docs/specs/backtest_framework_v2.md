# Specification: Backtest Engine V2 (Multi-Simulator Framework)

This document defines the architecture for the institutional backtesting framework, enabling comparative validation between idealized returns-based simulation and high-fidelity market simulation.

## 1. Overview

The framework decouples **Window Management** (rolling walk-forward logic) from **Market Simulation** (execution logic). This allows us to benchmark the impact of transaction costs, slippage, and liquidity on our optimization engines.

## 2. Simulation Backends

### 2.1 Returns Simulator (Internal Baseline)
- **Method**: Direct dot-product of weights and daily returns.
- **Daily Rebalancing**: Models daily rebalancing to target weights, ensuring mathematical parity with policy-based simulators.
- **Use Case**: Rapid alpha validation and idealized benchmarking.

### 2.2 CVXPortfolio Simulator (Convex Policy)
- **Method**: Utilizes `cvxportfolio.MarketSimulator`.
- **Friction Models**:
    - **Slippage**: Default 5 bps (0.0005) per trade.
    - **Commission**: Default 1 bp (0.0001) per trade.
    - **Market Impact**: Volume-based quadratic impact (requires OHLCV data).
- **Cash Management**: Uses a stablecoin (USDT) as the base currency for the simulator's cash account.
- **Use Case**: Institutional implementation audit and "Slippage Decay" analysis.
- **Depth**: Supports full secular backtest depth (250-500+ days) with strict universe alignment and `fillna(0.0)` for contiguous returns matrices.

### 2.3 VectorBT Simulator (High-Performance Vectorized)
- **Method**: Utilizes `vectorbt.Portfolio.from_returns`.
- **Friction Models**:
    - **Slippage**: Default 5 bps per trade.
    - **Fees**: Default 1 bp commission.
- **Processing**: Numba-accelerated vectorized operations.
- **Use Case**: Fast event-driven simulation and large-scale parameter sweeps.
- **Alignment**: Calibrated to use raw periodic returns without internal shifts (zero lookahead).
- **Depth**: Supports full secular backtest depth.

## 3. Metrics & Standards

Every simulator must output a standardized result schema, utilizing **QuantStats** for mathematical consistency:
- **Returns**: Geometric cumulative return and annualized mean.
- **Risk**: Annualized Volatility, Max Drawdown, and CVaR (95%).
- **Efficiency**: Sharpe Ratio, **Sortino Ratio**, **Calmar Ratio**, and Win Rate.
- **Operations**: 1-way Turnover ($ \sum |w_{t} - w_{t-1}| / 2 $).

All backends are forced through the unified `calculate_performance_metrics` utility to ensure zero mathematical drift between simulators.

## 4. Dynamic Universe Rebalancing

The framework supports **Adaptive Selection** at each rebalancing step, enabling the portfolio to evolve as market regimes shift.
- **Dynamic Pruning**: Re-runs the "Natural Selection" phase at the start of every walk-forward window using only the trailing history available at that point in time (Point-in-Time safety).
- **Identity Evolution**: Allows the portfolio to rotate out of stale assets and into new market leaders as correlations and momentum diverge within clusters.
- **Transition Costs**: Simulators (especially `CvxPortfolioSimulator`) correctly model the friction of closing old positions and opening new ones during these universe shifts.
- **Implementation**: Managed in `BacktestEngine.run_tournament` by calling `run_selection` from `scripts.natural_selection` at each iteration.

## 5. High-Fidelity Simulations

To ensure backtest results mirror real-world implementation, the framework employs several advanced modeling techniques:

### 5.1 Point-in-Time (PIT) Risk Auditing
The backtester no longer uses static risk scores. At each window start, it executes the production `AntifragilityAuditor` on the training returns. This ensures that the optimizer reacts to historical tail-risk events (e.g., flash crashes) just as it would in live production.

### 5.2 State Persistence (Cross-Window Transitions)
Simulators maintain position state between walk-forward windows.
- **Friction Continuity**: When moving from Window N to Window N+1, the simulator calculates transaction costs for the delta between the *realized ending weights* of the previous window and the *target weights* of the new window.
- **Cash Management**: Residual cash and dividends are preserved across the simulation timeline.

### 5.3 Multi-Engine Benchmarking (The 4D Tournament)
The `Tournament` mode evaluates a 4D matrix of `[Simulator] x [Selection Spec] x [Engine] x [Profile]`. This allows us to isolate the performance impact of pruning logic versus weighting logic.

#### Dimensions:
- **Simulators**: `ReturnsSimulator` (Idealized), `CvxPortfolioSimulator` (High-Fidelity).
- **Selection Specs**: Controlled by feature flags (e.g., `feat_selection_darwinian`, `feat_selection_robust`). Standard specs include `Darwinian (V3)`, `Robust (V3)`, `Relative (V2)`, `Passive (Legacy)`.
- **Engines**: `Custom`, `skfolio`, `Riskfolio`, `PyPortfolioOpt`, `CvxPortfolio`.
- **Profiles**: `MinVar`, `HRP`, `MaxSharpe`, `Barbell`, `EqualWeight`.

### 5.4 Alpha Isolation (Tiered Benchmarking)
The framework isolates alpha sources by comparing returns across three distinct tiers:

1. **Tier 1: Raw Pool EW ($R_{raw}$)**: Equal-weighted basket of all candidates discovered by scanners, before any pruning.
2. **Tier 2: Filtered EW ($R_{filtered}$)**: Equal-weighted basket of candidates passing a specific **Selection Spec**.
3. **Tier 3: Optimized ($R_{optimized}$)**: Weights produced by the risk engine using the filtered universe.

**Metric Equations:**
- **Selection Alpha ($A_s$):** $R_{filtered} - R_{raw}$ (Value of statistical pruning).
- **Optimization Alpha ($A_o$):** $R_{optimized} - R_{filtered}$ (Value of portfolio optimization).
- **Selection Efficiency:** The ratio of $A_s$ to total excess return.

**Baseline taxonomy**: The only official baseline profiles are `market` and `benchmark` (see `docs/specs/optimization_engine_v2.md`). `raw_pool_ew` is a backtest-only **selection benchmark baseline** used to isolate selection alpha and is not an optimization profile.
- **Risk profile comparisons**: Use `benchmark` as the default baseline when comparing risk profiles inside the active universe; use `market` for simulator calibration.
- **Selection alpha**: Use **canonical raw_pool_ew** vs **selected benchmark** to measure $A_s$.

#### Raw Pool Baseline: Universe Source (Canonical vs Selected)
The `raw_pool_ew` baseline must support two universe sources:
1. **Canonical**: `portfolio_candidates_raw.json` (post-merge canonical universe, pre-selection).
2. **Selected**: `portfolio_candidates.json` (natural-selection winners).

**Rule**: `raw_pool_ew` must be selection-mode invariant. Changing selection mode must not change `raw_pool_ew` unless the **universe source** is explicitly switched.

**Control**: Expose a single flag to choose the universe source (default: `selected` for backward compatibility):
- `TV_RAW_POOL_UNIVERSE=selected|canonical` (primary, matches `TV_` settings prefix)
- `RAW_POOL_UNIVERSE=selected|canonical` (supported when run via the production pipeline env promotion)

**Audit**: The audit ledger must record the universe source, symbol count, and returns hash for each `raw_pool_ew` window so the baseline is fully reproducible.

**Current Status (2026-01-03)**:
- **Implemented**: `scripts/backtest_engine.py` honors `raw_pool_universe` (`selected` default) and resolves `canonical` via `data/lakehouse/portfolio_candidates_raw.json` when present.
- **Fallbacks**: If the canonical list is empty or has zero overlap with the returns matrix, it automatically falls back to `selected`.
- **Baseline construction**: `raw_pool_ew` weights are equal-weighted across valid raw-pool symbols, excluding `benchmark_symbols`, and only symbols with full window data are retained.
- **Coverage constraint**: Canonical returns must include at least one contiguous `train + test + 1` window aligned to the backtest index. If canonical history starts later than the selected index, no valid windows will exist unless `start_date` is shifted to the canonical start (or windows are shortened).
- **Selection baseline**: Same-universe invariance validated across selection modes (canonical v3/v3.2 and selected v3/v3.2). Guardrail automation remains open.
- **Audit gap**: `raw_pool_symbol_count` and `raw_pool_returns_hash` are now recorded for `raw_pool_ew` windows, but historical runs may not include these fields.
- **Canonical wiring**: `raw_pool_ew` uses `data/lakehouse/portfolio_returns_raw.pkl` when present; canonical returns are generated in `make data-prep-raw`.

**Design Goals**:
- **Selection invariance**: `raw_pool_ew` must be identical across selection modes when the universe source is unchanged.
- **Invariance protocol**: Validate by running the same `TV_RAW_POOL_UNIVERSE` under multiple selection modes; do **not** compare canonical vs selected as an invariance test.
- **Canonical-first**: When `canonical` is requested, build and use a canonical returns matrix (or per-window slice) sourced from `portfolio_candidates_raw.json`.
- **Explicit provenance**: Each window must record `universe_source`, symbol count, and the returns matrix hash in `audit.jsonl`.
- **Graceful degradation**: If canonical inputs are missing, log a single warning and fall back to `selected` without silent behavior changes.
- **Benchmark isolation**: Keep benchmark symbols out of `raw_pool_ew` weights unless explicitly requested.
- **Stability gate**: If `raw_pool_ew` window coverage is incomplete or invariance fails, mark it as **diagnostic only** and exclude it from baseline comparisons.
- **Validation**: After canonical repairs, run a production-profile tournament with `TV_RAW_POOL_UNIVERSE=canonical` (and a canonical-aligned `start_date` when needed) to confirm non-zero windows and stable baseline metrics.

**Selection Audit Linkage**:
- Each tournament run must archive `selection_audit.json` (or `.md`) and record its hash in `audit.jsonl`.
- This bridges the canonical → selected provenance with selection alpha metrics (`raw_pool_ew` vs `benchmark`).

**Metadata Gate (Pre-Tournament)**:
- **Requirement**: Candidate manifests must include `tick_size`, `lot_size`, and `price_precision` before any selection or tournament run.
- **Source of truth**: Vetoes use the candidate manifests, not `portfolio_meta*.json`.
- **Operational step**: Run `scripts/enrich_candidates_metadata.py` after `data-prep-raw` and after `port-select`.

### 5.5 High-Fidelity Simulations
To eliminate the "First-Trade Bias" (where starting from 100% cash creates an artificial spike in turnover and transaction costs), the engine supports **Warm-Start Initialization**.
- **Mechanism**: The backtester attempts to load the last implemented state from `data/lakehouse/portfolio_actual_state.json`.
- **Initialization**: If found, the weights of the *first* walk-forward window are compared against these actual holdings. Transaction costs are only calculated for the delta.
- **Fallback**: If no state file exists, the simulation assumes a start from 100% Cash (Institutional Conservative bias).

## 12. Rebalance Fidelity (Drift vs. Reset)

The framework supports two rebalancing modes controlled by the `feat_rebalance_mode` flag:

### 12.1 Daily Reset (`daily`)
The portfolio is mathematically reset to the target weights at the end of every trading day. This is the legacy research mode used for purely statistical risk-parity studies. It ignores the "Drift Risk" that occurs when assets diverge within a rebalance period.

### 12.2 Window Drift (`window`)
Target weights are established only on the first day of the walk-forward window. Assets are allowed to drift based on their realized price returns for the remainder of the period (e.g., 20 days). This provides a high-fidelity validation of the actual implementation slippage.

## 13. Directional Integrity (Scanner-Locked)

To maintain strategy-locked alpha, the backtester enforces **Scanner-Locked Directions**:
- **Long-Only Scanners**: Assets discovered via long-only technical filters are strictly constrained to positive weights ($w \ge 0$).
- **Short-Only Scanners**: Assets discovered via short-only technical filters are strictly constrained to negative weights ($w \le 0$).
- **Borrow Costs**: Simulators apply an annualized borrow fee (default 2% p.a., gated by `feat_short_costs`) to all short positions to reflect institutional financing friction.

## 6. Institutional Standards (2025 Standard)
...


| Parameter | Value | Description |
| :--- | :--- | :--- |
| **Lookback** | 500 Days | Historical depth for discovery and secular validation. |
| **Train Window** | 252 Days | Full trading year history for optimization history buffer. |
| **Test Window** | 20 Days | Rolling validation window. |
| **Threshold** | 0.55 | Tighter clustering distance for high-conviction groups. |
| **Top N** | 1 | Focus capital on the single lead alpha asset per cluster. |
| **Baseline** | `AMEX:SPY` | Primary benchmark for all multi-asset comparisons. |
| **Friction** | 5bps Slippage / 1bp Commission | Real-world execution modeling. |

## 7. Multi-Calendar Correlation Logic & Index Integrity

The framework supports mixed calendars (24/7 Crypto + 5/7 TradFi).
- **Index Standard**: All returns and prices are strictly **Timezone Naive**. This prevents slicing errors and ensures consistency across disparate optimization engines (`cvxpy`, `skfolio`, `vectorbt`).
- **Sanitization**: Loaders implement "Ultra-Robust" element-wise index stripping (`replace(tzinfo=None)`) to handle contaminated indices from external sources.
- **Portfolio Returns**: Preserve all trading days (sat/sun included for crypto).
- **Benchmark Alignment**: TradFi benchmarks (`SPY`) are mapped to the portfolio calendar. Benchmark returns on weekends are treated as `0.0`, ensuring that weekend crypto alpha is captured without benchmark bias.
- **No Padding**: The returns matrix no longer zero-fills non-trading days for TradFi assets, preserving statistical variance and Sharpe accuracy.

## 8. Tournament Matrix (3D Benchmarking)

The "Tournament" evaluates a 3D matrix of `[Simulator] x [Engine] x [Profile]`.

### 8.1 Dimensions
- **Simulators**: `ReturnsSimulator` (Idealized), `CvxPortfolioSimulator` (Convex Policy), `VectorBTSimulator` (Vectorized Event-Driven).
- **Engines**: `Custom (Cvxpy)`, `skfolio`, `Riskfolio-Lib`, `PyPortfolioOpt`, `CvxPortfolio`, **`Market`**.
    - **Regularization**: All Mean-Variance based engines (Custom, Skfolio, Riskfolio) must utilize **L2 Regularization** (Ridge) to prevent overfitting and "Ghost Alpha".
        - `custom`: `0.05 * sum(weights^2)` penalty.
        - `skfolio`: `l2_coef=0.05`.
        - `riskfolio`: `l=0.05`.

### 2. Simulators (Execution Fidelity)

The framework supports multiple simulation backends to triangulate performance:

1.  **`CvxPortfolio` (Primary)**: 
    - **Role**: High-fidelity source of truth.
    - **Features**: Accurate slippage, spread, and commission modeling. Correctly handles turnover and friction.
    - **Status**: **Stable**. Used for all final validations.

2.  **`Custom` (Baseline)**:
    - **Role**: Fast, idealized execution.
    - **Features**: Idealized rebalancing (no friction). Good for checking logic but overestimates net returns.
    - **Status**: **Stable**.

3.  **`VectorBT` (Experimental)**:
    - **Role**: High-performance vectorized backtesting.
    - **Features**: Extremely fast for large datasets.
    - **Status**: **Unstable**. Currently reports 0.00% turnover for weight-based rebalancing strategies due to signal alignment issues. Under investigation (see `docs/research/vectorbt_anomaly_investigation.md`).
- **Profiles**: `MinVar`, `HRP`, `MaxSharpe`, `Antifragile Barbell`, `BuyHold`.

### 8.2 Hierarchical Risk Parity (HRP) Standards
The HRP profile aims for equal risk contribution across hierarchical clusters.
- **Custom Engine**: Implements a **Convex Risk Parity** approximation using a log-barrier objective on cluster benchmarks.
- **Linkage**: The standard production linkage is **Ward** on **Intersection Correlation**.

4.  **`Market` (Institutional Benchmark)**:
    - **Goal**: Standard institutional hurdle rate and **Simulator Calibration**.
    - **Strategy**: Equal-weight allocation across fixed high-liquidity indices (default: `["AMEX:SPY"]`).
    - **Logic**: Independent of active scanning universe pruning.
    - **Calibration Role**: By running a fixed-weight benchmark through all simulators, we calibrate for:
        - **Return Parity**: Ensuring simulators agree on the base return of known assets (e.g., SPY).
        - **Turnover Baseline**: Measuring the drift-induced turnover vs. rebalancing-induced turnover.
        - **Friction Sensitivity**: Identifying how different slippage/cost models impact a static portfolio.

### 3. Audit & Reporting Fidelity (Jan 2026)

To ensure institutional-grade transparency, the reporting engine now extracts deep context from the **Audit Ledger**:

- **Simulator Synchronization**: All simulators are calibrated to a normalized **Turnover Metric** defined as `Sum(Abs(Trades)) / 2 / Portfolio Value`.
    - `CvxPortfolio`: Normalized (divided by 2.0). High-fidelity friction modeling.
    - `VectorBT`: Window-Aware. Normalized (divided by 2.0). Fast vectorized execution.
    - `Custom`: Frictionless baseline. Rebalance-delta turnover.
- **Cash Awareness**: Simulators are synchronized to treat unallocated weight as Cash (0% return), preventing volatility inflation in the baseline engine.
- **Benchmark Consistency**: All simulators are verified against a fixed single-asset benchmark (e.g., SPY) to ensure zero-bias return parity.

### 4. Simulator Fidelity & Calibration Standards (Jan 2026)

To maintain a "Source of Truth" for quantitative results, the following calibration standards are enforced:

| Standard | Requirement | Mechanism |
| :--- | :--- | :--- |
| **Return Parity** | Annualized Return difference < 0.5% | Fixed Day-0 price alignment across all backends. |
| **Turnover Sync** | Metric: `Sum(Abs(Trades)) / 2 / Value` | Harmonized normalization across CVX, VBT, and Custom. |
| **Rebalance Mode** | Strict adherence to `feat_rebalance_mode` | Syncing 'window' vs 'daily' logic to ensure identical churn. |
| **Audit Trail** | Per-window weight & meta persistence | Hash-chained ledger (`audit.jsonl`) for 100% reproducibility. |

The `CvxPortfolio` simulator remains the **High-Fidelity Reference**, while `VectorBT` is the **High-Performance Exploratory** engine.

### 5. Backend Integrity & Dependency Management (Jan 2026)

To ensure the reproducibility of tournament results across institutional environments, the following dependency standards are enforced:

- **Single Source of Truth**: All optimization backends (`skfolio`, `riskfolio-lib`, `pyportfolioopt`, `clarabel`, `cvxportfolio`) are formally codified in `pyproject.toml` under the `[project.optional-dependencies]` section.
- **Lockfile Primacy**: The `uv.lock` file is the immutable record of the production-validated environment. All development and CI/CD runs must use `uv sync --all-extras` to ensure environment parity.
- **Multi-Backend Synchronization**:
    - **`engines`**: Contains BSD/MIT licensed solvers (`skfolio`, `riskfolio`, `pyportfolioopt`, `clarabel`).
    - **`engines-gpl`**: Isolates `cvxportfolio` to prevent license contamination of the core library.
    - **`analytics`**: Contains reporting and simulation tools (`quantstats`, `vectorbt`).
- **Compatibility Layer**: Autogenerated `requirements.txt` and `dev-requirements.txt` are provided for legacy CI/CD pipelines but are derived exclusively from the `uv` lockfile.


## 10. Unified QuantStats Reporting
The reporting pipeline is rebased entirely on **QuantStats** to ensure mathematical consistency.
- **Slippage Decay Audit**: Generates a detailed comparison between idealized and realized returns to quantify implementation friction (Gated by `feat_decay_audit`).

## 11. Alpha Isolation (Selection vs. Optimization)

The framework isolates alpha sources by comparing three distinct tiers:
1. **Raw Pool EW**: Equal-weighted basket of all candidates found during discovery.
2. **Filtered EW**: Equal-weighted basket of the Top N assets per cluster selected by the `NaturalSelection` logic.
3. **Optimized Weights**: Cluster-weighted allocation produced by the optimization engine (e.g., MinVar, HRP).

- **Selection Alpha**: Measured as the spread between Tier 2 and Tier 1. This quantifies the value of the pruning logic.
- **Optimization Alpha**: Measured as the spread between Tier 3 and Tier 2. This quantifies the value of the statistical weighting engine.
