# Production Workflow v2

## 1. Overview
The production workflow is divided into three distinct phases to ensure data integrity, alpha purity, and efficient execution.

### Phase 1: Data Operations (`flow-data`)
**Goal**: Identify candidates, ingest raw market data, and prepare the Lakehouse.
**Trigger**: Scheduled (e.g., Daily/Weekly) or Manual.

1.  **Discovery (`scan-run`)**:
    - Executes composable scanners defined in `configs/scanners/`.
    - Outputs candidate lists (JSON) to `data/export/<RUN_ID>/`.
    - **Parallelism**: Scanners run independently.

2.  **Ingestion (`data-ingest`)**:
    - **Parallel Execution**: Uses `xargs -P` to process candidate files concurrently.
    - **Idempotency**: Checks `freshness_hours` to skip recently updated assets.
    - **Toxic Guard**: Validates daily returns ($|r| < 500\%$) immediately after fetch.

3.  **Metadata (`meta-ingest`)**:
    - Refreshes symbol metadata (tick sizes, lot sizes) from exchanges.

4.  **Feature Ingestion (`feature-ingest`)**:
    - Fetches/Calculates technical indicators (TradingView technicals).

5.  **Feature Backfill (`feature-backfill`)**:
    - **Dynamic Backtesting**: Reconstructs historical technical ratings (Time x Symbol) from OHLCV data.
    - Produces `data/lakehouse/features_matrix.parquet` for point-in-time correct simulations.

### Phase 2: Alpha Production (`flow-production`)
**Binance Ratings Baselines (Atomic LONG/SHORT)**:
- Runbook: `docs/runbooks/binance_spot_ratings_all_long_short_runbook_v1.md`
- One-command: `make flow-binance-spot-rating-all-ls`

**Goal**: Generate a single-sleeve portfolio (e.g., "Crypto Trend Following" or "US Equities").
**Orchestrator**: `scripts/run_production_pipeline.py`

**Optimization Flags**:
- `--skip-analysis`: Skips heavy visualizations (Clustermaps, Factor Maps).
- `--skip-validation`: Skips full backtesting (useful for rapid iteration).

1.  **Aggregation**:
    - Reads candidates from Lakehouse.
    - Applies "Strict Health" filters (no missing bars).

2.  **Natural Selection (`port-select`)**:
    - Applies HTR v3.4 (Hierarchical Threshold Relaxation).
    - Filters for secular history and momentum.

3.  **Strategy Synthesis**:
    - Inverts Short candidates with a -100% loss cap ($R_{syn,short} = -clip(R_{raw}, upper=1.0)$).
    - Construct "Strategy Atoms".
    - For directional sleeves (e.g., `binance_spot_rating_all_short`), certify inversion correctness with the Directional Correction Sign Test (`docs/specs/directional_correction_sign_test_v1.md`).
    - If `feat_directional_sign_test_gate_atomic` is enabled, the production orchestrator fails fast on sign-test violations and persists `directional_sign_test_pre_opt.json` / `directional_sign_test.json` in the run directory.

4.  **Pre-Opt Analysis (`port-pre-opt`)**:
    - **Critical Path**: Calculates Correlation Clusters (HRP), Antifragility Stats, and Regime Caps.
    - Required for Optimization logic.

5.  **Optimization (`port-optimize`)**:
    - Runs Decision-Naive Solvers (HRP, MinVar, MaxSharpe).
    - Enforces **Stable Sum Gate** ($W_{sum} > 1e-6$).

6.  **Reporting (`port-report`)**:
    - Generates unified tearsheets and weight files immediately.
    - If `feat_directional_sign_test_gate_atomic` is enabled, runs `scripts/validate_atomic_run.py` as a final artifact + audit gate.

7.  **Validation (`port-test`)** *(Optional)*:
    - Runs backtests (VectorBT/Nautilus) on the optimized weights.
    - **Dynamic Filtering**: Uses `features_matrix.parquet` to filter eligible assets at each historical rebalance point.
    - Generates forensic reports.

8.  **Post-Analysis (`port-post-analysis`)** *(Optional)*:
    - Generates heavy visualizations (Cluster Maps, Factor Maps, Drift Monitors).

### Phase 3: Meta-Portfolio (`flow-meta-production`)
**Goal**: Combine multiple sleeves into a unified "Fractal" portfolio.
**Orchestrator**: `scripts/run_meta_pipeline.py`

1.  **Parallel Sleeve Execution**:
    - Uses **Ray** to execute child profiles (e.g., `crypto_long`, `crypto_short`) in parallel.
    - Each sleeve runs a full Phase 2 cycle.

2.  **Directional Correction Gate (Sign Test)**:
    - When enabled via `feat_directional_sign_test_gate`, the meta orchestrator runs the Directional Correction Sign Test before aggregation.
    - Fails fast if any pinned sleeve violates SHORT inversion semantics at the sleeve boundary.

3.  **Recursive Aggregation**:
    - Builds a "Meta-Returns" matrix (Sleeves become Assets).

4.  **Meta-Optimization**:
    - Allocates risk budget across sleeves (e.g., Risk Parity).

5.  **Flattening**:
    - Projects meta-weights down to individual assets.

## 2. Key Improvements (v2)
- **Parallel Data Ingestion**: Makefile updated to use `xargs -P` for faster `data-ingest`.
- **Fractal Isolation**: Meta-portfolios run in isolated workspaces (`data/runs/<RUN_ID>`) to prevent leakage.
- **Fail-Fast Health**: Pipeline aborts immediately if "Strict Health" audit fails.
