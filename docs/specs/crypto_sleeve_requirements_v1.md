# Crypto Sleeve Requirements Specification v3.6.2

## 1. Overview

### 1.1 Purpose
Define the institutional requirements for the crypto production sleeve within the multi-sleeve meta-portfolio architecture.

### 1.2 Scope
This specification covers the crypto asset discovery, selection, optimization, and backtesting infrastructure for BINANCE-only production deployment using the `uv` native workflow.
Includes standard certification for Rating-Based Strategy Benchmarks:
- `binance_spot_rating_all_long/short`
- `binance_spot_rating_ma_long/short`

Atomic pipeline runbook (baseline ratings):
- `docs/runbooks/binance_spot_ratings_all_long_short_runbook_v1.md`

### 1.3 Status
**Production Certified** (2026-01-16) - Deep Audit Standard v3.6.4.
**Rerun Scheduled** (2026-01-18) - Meta-Portfolio stress test for All/MA Rating profiles.
**Note**: Rating-based profiles are currently backtested on "Latest-Snapshot" data. Full validation pending historical feature accumulation (v3.6.5).

### 3.3 DataOps & Infrastructure
- **Ingestion Hygiene**: 
    - **Export Isolation**: Ingestion processes MUST NOT generate raw OHLC/Indicator files in the export directory.
    - **Consolidation**: Disparate scanner outputs MUST be automatically aggregated into `portfolio_candidates.json` before metadata enrichment.
- **Traceability**:
    - **Instrument Mapping**: Deduplication processes MUST preserve discarded instrument metadata (e.g., PERP symbols) as `alternatives` within the canonical (SPOT) candidate record to support downstream execution routing.
- **Run Identity**: Every execution MUST be traceable via a unique `RUN_ID`.
- **Artifact Retention**: Raw candidates, selected portfolios, and returns matrices MUST be persisted to the `artifacts/` tree.

### 3.4 Selection Ranking & Signal Dominance (v3.6.4)
- **Pluggable Ranking**: The Selection Policy MUST support a configurable ranking interface via the manifest:
    - **Method**: `mps` (default) or `signal` (raw feature).
    - **Direction**: `descending` (default, High Score=Bullish) or `ascending` (Low Score=Bearish).
- **Signal Dominance**: Profiles MUST be able to assert a "Primary Signal" via `dominant_signal` configuration:
    - **Boost**: The primary signal weight is significantly increased (e.g., 3.0x).
    - **Dampen**: Competing signals (e.g., generic Momentum) are automatically dampened to prevent alpha dilution.
    - **Use Case**: Enables specialized strategies like `Rating MA Short` (Ascending Sort + MA Dominance) to function alongside generic `Rating All` strategies.

### 3.5 Historical Feature Persistence (v3.6.5)
- **Requirement**: The system MUST implement a mechanism to capture and persist discovery-layer signals (e.g., `Recommend.All`, `Recommend.MA`) on a daily basis.
- **Rationale**: To resolve the "Discovery-Backtest Regime Mismatch" where backtests rely on present-day scanner results for historical rebalancing.
- **Policy**: Low-performing profiles (e.g., `Rating MA`) MUST NOT be discarded. They are preserved in `active` state to facilitate data collection for future validation once sufficient history is accumulated.

### 3.6 Synthetic Rating Reconstruction (v3.6.5)
- **Requirement**: The system MUST be able to generate historical `Recommend.MA` and `Recommend.Other` signals from raw OHLCV data that correlate > 0.9 with TradingView's live values.
- **Rationale**: To resolve the "Discovery-Backtest Regime Mismatch" and enable true historical backtesting of Rating-based strategies without waiting for months of data accumulation.
- **Implementation**: Utilize `pandas-ta` to replicate the Moving Average (15 components) and Oscillator (11 components) ensemble logic defined in the Feature Composition spec.

### 3.7 Meta-Portfolio Architecture
The system MUST support the [Fractal Hierarchical Meta-Portfolio Specification](fractal_meta_portfolio_v1.md), including recursive nesting, weighted branch aggregation, and physical asset collapse.

### 3.8 Specs Driven Development (SDD) Flow (v3.6.7)
- **Mandatory Lifecycle**: Every quantitative feature MUST follow the formal [SDD Flow](sdd_flow.md):
    1. **Spec**: Update Requirements/Design docs first.
    2. **Build**: Implementation with atomic commits.
    3. **Verify**: Rerun full production pipelines.
    4. **Audit**: Trace realized results using ledger logs and cluster trees.
- **Certification Gate**: Deployment to paper/live trading is prohibited without a signed-off forensic audit report in `docs/reports/`.

### 3.9 Atomic Correctness & Completeness (v3.6.6)
- **Full Spectrum Requirement**: All production-grade sleeves MUST generate a full return set (8 standard profiles: `hrp`, `min_variance`, `max_sharpe`, `equal_weight`, `barbell`, `market`, `benchmark`, `risk_parity`) to be eligible for Meta-Portfolio inclusion.
- **Proxy Status**: Use of Proxies (MinVar for HRP) is permitted for pipeline resilience during development but marks the sleeve as **DEGRADED** in the final certification report.
- **Validation Gate**: A sleeve is only considered **CERTIFIED** once all 8 profiles are generated natively without numerical errors.

### 3.10 Stability & Wealth Continuity
- **Wealth Persistence**: Simulations MUST persist absolute wealth (in $ or wealth units) across rebalance boundaries to maintain wealth-process continuity.
- **Outlier Guard**: Daily returns MUST be clipped at reasonable thresholds (e.g., -99.9% to +500%) during reporting to prevent numerical artifacts from corrupting summary CAGR calculations.
- **Bankruptcy Logic**: Portfolios dropping below a defined wealth floor (e.g., 1%) MUST be liquidated to cash to reflect total strategy failure.
- **Simulator Parity**: The Sharpe Ratio drift between vector-based and friction-based simulators MUST be monitored and documented (Target: Drift < 0.20).

### 3.11 Portfolio Normalization
- **Gross Exposure Cap**: Simulators MUST enforce a strict 1.0 Gross Exposure (sum of absolute weights) at the rebalance point to prevent unintended margin-driven volatility spikes.
- **Cash Buffering**: Residual equity after meeting target weights MUST be held in cash to ensure the sum of all weights (including cash) is exactly 1.0.

### 2.12 Short Selling & Margin Standards
| Requirement ID | Priority | Status | Description |
|----------------|----------|--------|-------------|
| CR-700 | MUST | | **Borrow Cost Simulation**: Simulators MUST apply a dynamic borrow fee (default 0.01% daily) to all negative-weight positions to model the cost of leverage and inventory scarcity. |
| CR-710 | MUST | | **Liquidation Protocol**: The system MUST enforce a "Maintenance Margin" check (default 50%). If equity drops below this threshold relative to gross exposure, a forced liquidation event is triggered in the backtest. |
| CR-720 | MUST | | **Order Side Explicitization**: The Order Generator MUST distinguish between `SELL` (Long Closure) and `SELL_SHORT` (Short Opening) based on current position state, never assuming a single "Sell" verb covers both. |
| CR-730 | MUST | | **Hard-to-Borrow Veto**: The Selection Pipeline MUST accept a `borrow_availability` metadata feed and veto SHORT candidates with low inventory (preventing "Naked Short" simulation). |
| CR-750 | MUST | ✅ | **Metric Verification Standard**: All backtest results MUST undergo independent verification by the `stable_institutional_audit.py` script. The script MUST re-calculate Sharpe, AnnRet (TWR), and MaxDD from raw daily return series to ensure 100% agreement with simulator-reported metrics. |
| CR-760 | MUST | ✅ | **Geometric Performance Standard**: Annualized Return MUST be calculated using geometric compounding (CAGR) via the `quantstats` package to accurately reflect the impact of volatility drag, especially in crypto regimes. |
| CR-770 | MUST | | **Pillar 2 Strategy Attribution**: Every backtest window MUST record the contribution of each strategy atom (Logic/Direction) to the total window return to ensure transparent alpha attribution. |
| CR-780 | MUST | ✅ | **Data Ingestion Purity Gate**: The data preparation pipeline MUST enforce 100% ticker alignment across return matrices and metadata. Discrepancies MUST trigger a pipeline halt to prevent selection bias from missing data. |
| CR-790 | MUST | ✅ | **Deep Forensic Funnel Trace**: Every backtest window MUST record the candidate count at each filtering stage (Universe -> Discovery -> Refinement -> Selection) to identify alpha leakage bottlenecks. |
| CR-114 | MUST | ✅ | **Alpha Immersion Floor**: The history floor for crypto assets is set to 90 days for production; this maximizes participation of high-momentum listings while maintaining statistical validity. |
| CR-116 | MUST | ✅ | **Antifragility Significance**: Antifragility scores must be weighted by a significance multiplier ($\min(1.0, N/252)$) to prevent low-history assets from dominating the ranking. |
| CR-115 | MUST | ✅ | **Cluster Diversification standard**: The selection engine must pick up to the Top 5 assets per direction (Long/Short) within each cluster to prevent single-asset factor concentration. |
| CR-181 | MUST | ✅ | **Directional Normalization Standard**: Returns matrices passed to risk and selection engines must be "Alpha-Aligned" (Synthetic Long) by inverting returns for assets identified as SHORT in the current window ($R_{synthetic} = \text{sign}(M) \times R_{raw}$). |
| CR-182 | MUST | ✅ | **Late-Binding Directional Assignment**: Asset direction must be dynamically determined at each rebalance window using recent momentum to ensure factor purity and protect against regime drift. |
| CR-183 | MUST | ✅ | **Direction-Blind Portfolio Engines**: All allocation engines (HRP, MVO, Barbell) must operate on the normalized "Synthetic Long" matrix, ensuring consistent logic across all strategy types without direction-specific code paths. |
| CR-184 | MUST | ✅ | **Simulator Reconstruction**: Backtest simulators must utilize the `Net_Weight` derived from synthetic weights and assigned directions ($W_{net} = W_{synthetic} \times \text{sign}(M)$) to execute trades correctly. |
| CR-185 | MUST | ✅ | **Lookahead Bias Prevention**: Training and testing datasets MUST be strictly partitioned using exclusive indices. The selection engine MUST NOT observe any part of the realized return window during its recruitment phase. |
| CR-190 | MUST | ✅ | **TDD Hardening**: Critical risk components (inversion, direction assignment) are protected by unit tests to ensure logical integrity. |
| CR-191 | MUST | ✅ | **Feature Flag Control**: Experimental risk features are gated behind specific toggles in `TradingViewScraperSettings` to allow for safe production rollouts. |
| CR-210 | MUST | ✅ | **Selection Scarcity Resilience**: The pipeline must implement the Selection Scarcity Protocol (SSP) to handle windows where high-resolution filters (Entropy Order=5) yield sparse winner pools (n < 3). |
| CR-211 | MUST | ✅ | **Solver Tolerance**: Optimization engines must implement explicit error handling and fallback logic for solver-specific failures (e.g., CVXPY infeasibility, skfolio recursion) triggered by low asset counts. |
| CR-212 | MUST | ✅ | **Balanced Selection Standard**: The selection engine must ensure a minimum pool of 15 candidates per window by falling back to the top-ranked rejected assets (by alpha score) if primary filters are too restrictive. |
| CR-213 | MUST | ✅ | **Global Metadata Fallback**: To prevent "Sparsity Vetoes" of high-alpha assets, the pipeline must provide default execution parameters (tick_size, lot_size) for recognized exchange classes (e.g., BINANCE_SPOT) if local metadata is missing. |
| CR-214 | MUST | ✅ | **HTR Standard**: The selection engine must implement the 4-stage Hierarchical Threshold Relaxation loop (Strict -> Spectral -> Factor Representation -> Balanced Fallback) to ensure $N \ge 15$. |
| CR-220 | MUST | ✅ | **Dynamic Ridge Scaling**: The system must iteratively apply shrinkage (diagonal loading) to the covariance matrix if the condition number (Kappa) exceeds a configurable threshold (default 5000), ensuring numerical stability for solvers. |
| CR-221 | MUST | ✅ | **Adaptive Safety Protocol**: The `adaptive` meta-engine must default to an **Equal Risk Contribution (ERC)** fallback profile (or other configurable safety profiles like EW) when sub-solvers fail or during warm-up periods. |
| CR-230 | MUST | ✅ | **Toxicity Hard-Stop**: HTR Stage 3/4 recruitment must never include assets failing a strict entropy limit (default 0.999 for Crypto), ensuring factor representation without alpha dilution. |
| CR-232 | MUST | ✅ | **Backend Purity**: Optimization engines must not use shared base-class fallbacks; each backend (`skfolio`, `riskfolio`, etc.) must execute its own solver or return explicit failure to ensure performance differentiation. |
| CR-233 | MUST | ✅ | **Hybrid Barbell**: The `barbell` strategy must optimize its core layer using the engine's native solver, allowing for backend-specific risk-management profiles. |
| CR-240 | MUST | ✅ | **Baseline Selection Standard**: The system must provide a `baseline` selection engine that passes through all candidates to the portfolio engines, enabling quantification of Selection Alpha. |
| CR-250 | MUST | ✅ | **Statistical Sample Floor**: Forensic audits and tournaments must utilize at least 15 candidates (via HTR Stage 4 fallback) to ensure numerical differentiation between solvers and prevent constrained convergence to bit-perfect identical weights. |
| CR-260 | MUST | ✅ | **Directional Synthetic Longs**: Portfolio engines must handle `SHORT` candidates by inverting their returns before optimization ($R_{syn,short} = -clip(R_{raw}, upper=1.0)$) to enforce the -100% short loss cap and ensure decision-naive solvers treat shorts as alpha-positive stability contributors. |
| CR-261 | MUST | ✅ | **Regime-Direction Alignment**: The `MarketRegimeDetector` must influence the late-binding asset direction, specifically enforcing tighter filters on `LONG` candidates during `CRISIS` or `TURBULENT` regimes. |
| CR-270 | MUST | ✅ | **Synthesis-Allocation Decoupling**: Decision logic (regime mapping, directional inversion) is abstracted into the Strategy Synthesis layer. Portfolio engines are "Decision-Naive" and operate only on processed return streams. |
| CR-271 | MUST | ✅ | **Atomic Strategy Interface**: The platform supports "Atomic Strategies" (Asset, Logic, TimeScale) as optimization candidates. Each Atom must have exactly ONE logic. |
| CR-280 | MUST | ✅ | **Complex Strategy Composition**: Supports ensembling atoms into complex strategies. Note: Strategic intents (like Barbell or Neutrality) are handled by Pillar 3 (Allocation) for global optimality. |
| CR-281 | MUST | ✅ | **Recursive Weight Flattening**: The Orchestrator supports mapping optimized strategy weights back to underlying physical assets for implementation. |
| CR-290 | MUST | ✅ | **Market Neutral Constraint**: Market neutrality is a native optimization constraint (not a profile), enabling beta-hedged Max-Sharpe/HRP portfolios. |
| CR-291 | MUST | ✅ | **Synthetic Hierarchical Clustering**: The Allocation layer performs hierarchical clustering on synthesized return streams to identify uncorrelated alpha factors. |
| CR-292 | MUST | ✅ | **Pillar 3 Strategy Status**: The `barbell` strategy is classified as a **Risk Profile** (Pillar 3) because it manages capital segmentation across provided alpha streams. |
| CR-300 | MUST | ✅ | **Experimental Guardrails**: High-impact experimental constraints (e.g., Market Neutrality) MUST be gated by feature flags (`feat_market_neutral`) and default to OFF for institutional stability. |
| CR-310 | MUST | ✅ | **Canonical Consolidation**: The Discovery stage MUST deduplicate symbols by economic identity (e.g., BTC, GC) across multiple venues, selecting the most liquid implementation to prevent fragmentation in the "Raw Pool." |
| CR-311 | MUST | ✅ | **Top-N Cluster Purity**: The selection engine MUST prioritize candidates by Log-MPS conviction score within each hierarchical cluster, ensuring the highest conviction representatives for each identified alpha factor. |
| CR-312 | MUST | ✅ | **History-Aware Sanitization**: The data preparation layer MUST enforce a configurable history floor (min_days_floor) and zero-variance filter to eliminate statistically insignificant assets before optimization. |
| CR-320 | MUST | ✅ | **Pass-through Baseline**: The system MUST provide a `baseline` engine that passes ALL valid candidates to quantify the "Gross Alpha" of the entire selection funnel. |
| CR-321 | MUST | ✅ | **Structural Baseline**: The system MUST provide a `liquid_htr` engine that performs hierarchical clustering but selects Top-N by liquidity (Value.Traded), isolating the "Statistical Alpha" added by Log-MPS scoring. |
| CR-330 | MUST | ✅ | **End-to-End Traceability**: Every production decision MUST be traceable from the initial L4 scanner signal through Identity Deduplication, Cluster Assignment, and final Portfolio Weighting. |
| CR-331 | MUST | ✅ | **Factor-Preserving Selection**: The selection pipeline MUST prioritize the highest-conviction Log-MPS representatives *within* each hierarchical cluster to ensure diversification across discovered alpha factors. |
| CR-400 | MUST | ✅ | **Stateless Pipeline Stages**: All v4 selection stages MUST be stateless. They receive a `SelectionContext` and return a modified `SelectionContext`. |
| CR-401 | MUST | ✅ | **Data Immutability**: The original `RawPool` input MUST never be modified; all enrichments are added as new columns or metadata layers in the context. |
| CR-402 | MUST | ✅ | **Schema-Validated Handover**: Every pipeline stage transition MUST be validated by a strict schema (Pydantic) to ensure end-to-end data integrity. |
| CR-403 | MUST | ✅ | **Pipeline Modularity**: The v4 pipeline architecture MUST support the hot-swapping of `ConvictionScorer` models without re-implementing clustering or selection logic. |
| CR-410 | MUST | ✅ | **Shadow Mode Execution**: The system MUST support running the v4 MLOps pipeline in parallel with the v3 Legacy engine for a configurable period ("Shadow Week") to validate stability before full cutover. |
| CR-420 | MUST | ✅ | **Structured Telemetry Segregation**: The Orchestrator MUST segregate granular `pipeline_audit` trails from scalar selection metrics. Telemetry MUST be persisted in the `data` field of the `AuditLedger` to ensure full traceability without bloating the KPIs namespace. |
| CR-430 | MUST | ✅ | **Selection Engine Coexistence**: The platform MUST maintain backward compatibility with legacy selection engines (v2.x, v3.x). These engines are preserved as \"Anchors\" for historical benchmarking while v4 serves as the modern MLOps standard. |
| CR-450 | MUST | ✅ | **Deep Window Traceability**: The audit ledger MUST record global timescale configurations (rebalance window, train/test windows) in the genesis block to ensure statistical reproducibility across different sampling frequencies. |
| CR-460 | MUST | ✅ | **Discovery-to-Selection Purity Audit**: Every tournament MUST quantify the alpha contribution of discovery-stage filters (L4 Scanners) by benchmarking against a 'No-Selection' Raw Pool to identify bottlenecks in the early alpha funnel. |
| CR-470 | MUST | ✅ | **Alpha Decay Monitoring**: The system MUST implement statistical rebalance-frequency audits (Grand Tournament Protocol) to identify the half-life of alpha signals and enforce a production rebalance floor (default <= 20 days). |
| CR-480 | MUST | ✅ | **Final Certification Protocol**: Prior to any major release, the system MUST undergo an exhaustive risk profile tournament across all selection-optimization-simulator combinations to ensure zero performance regression and 100% directional integrity. |
| CR-490 | MUST | ✅ | **Entropy-Aware Hardening**: During high-entropy regimes (DWT Entropy > 0.95), the selection pipeline MUST automatically tighten predictability vetoes to prevent factor dilution in unstable markets. |
| CR-500 | MUST | ✅ | **Per-Rebalance Portfolio Snapshots**: The audit ledger MUST record the full portfolio composition (Symbols, Weights, Directions) at every rebalance window to enable deep forensic attribution and slippage analysis. |
| CR-510 | MUST | ✅ | **Outlier Forensic Audit**: Every production run MUST undergo an automated outlier audit that identifies and justifies any statistically extreme Sharpe (>10) or Drawdown (<-30%) events at the window level. |
| CR-520 | MUST | ✅ | **Global Timescale Traceability**: The audit ledger MUST record all active timescales (train/test/rebalance/lookback) in the genesis block to ensure statistical reproducibility across different sampling frequencies. |
| CR-530 | MUST | ✅ | **Parallel Alpha Scoring**: For large candidate pools (N > 1000), the selection pipeline MUST utilize vectorized probability mapping to ensure selection latency remains within institutional bounds (< 2 seconds). |
| CR-540 | MUST | ✅ | **Sleeve Diversity Audit**: Every tournament report MUST include a 'Sleeve Diversity Score' calculating factor concentration across sectors to ensure the recruited winner pool remains orthogonal. |
| CR-550 | MUST | ✅ | **Vectorized Performance Standard**: The selection pipeline MUST achieve < 2s latency for universes of N=1000 using vectorized probability mapping (CR-530) to meet production throughput standards. |
| CR-560 | MUST | ✅ | **Rebalance Window Reproducibility**: The audit ledger MUST persist the exact rebalance timestamps and interval length (step_size) to ensure historical fidelity in meta-analysis and slippage modeling. |
| CR-590 | MUST | ✅ | **Mandatory 25% Cluster Cap**: All portfolio optimization backends MUST enforce a strict upper weight limit of 25% per cluster to prevent factor over-concentration, regardless of the user-provided `cluster_cap`. |
| CR-610 | MUST | ✅ | **Automated Deep Audit**: Every production-grade backtest MUST be accompanied by a comprehensive forensic report generated by `comprehensive_audit_v4.py`, verifying directional purity and volatility band compliance. |
| CR-620 | MUST | ✅ | **Tail-Risk Hard-Stop**: In the event of an automated outlier audit detecting Window Drawdown > 50%, the orchestrator MUST trigger a safety protocol (e.g., Ridge loading or Cash shift) for subsequent rebalances. |
| CR-630 | MUST | ✅ | **Fat-Tail Awareness**: The Selection Pipeline and Regime Detector MUST incorporate tail-risk metrics (Skewness, Kurtosis, CVaR) to penalize assets with unstable return distributions. |
| CR-631 | MUST | ✅ | **Tail-Risk Veto Standard**: The Selection Pipeline MUST enforce hard vetoes on assets with extreme Kurtosis (>20) or annualized volatility (>250%) to prevent factor dilution during high-entropy regimes. |
| CR-640 | MUST | ✅ | **Directional Balance Delegation**: Directional concentration limits (e.g., LONG/SHORT exposure caps) are delegated to the **Pillar 3 (Allocation)** layer. The selection pipeline provides the purified alpha pool, while the portfolio engine enforces strategy-specific risk policy. |
| CR-650 | MUST | ✅ | **Hard-Bounded Cluster Resolution**: The clustering stage MUST enforce a hard ceiling (default: 25) on factor resolution to ensure statistically significant branch variance for risk budgeting. |
| CR-660 | MUST | ✅ | **Simulator Liquidation Standard**: Portfolio backtest simulators MUST enforce a -100% liquidation floor. Any strategy reaching this threshold is considered failed, and subsequent rebalance returns are zeroed out to prevent "Negative Capital" artifacts. |
| CR-670 | MUST | ✅ | **Solver Health Gate**: Meta-aggregation scripts MUST automatically veto any atomic sleeve exhibiting a solver success rate below 75% to ensure the integrity of the meta-portfolio. |
| CR-671 | MUST | ✅ | **Recursive Aggregation Caching**: The meta-aggregation pipeline MUST utilize a content-hashed caching layer to eliminate redundant IO and compute in complex fractal strategy trees. |
| CR-672 | MUST | ✅ | **Forensic Outlier Reporting**: All meta-portfolio reports MUST include an automated forensic table identifying window-level anomalies (Sharpe > 10, Return > 1000%) to provide early warning of solver divergence. |
| CR-680 | MUST | ✅ | **Ray-Based Parallelization**: The meta-aggregation orchestrator MUST utilize Ray for concurrent sleeve execution to minimize wall-clock production time while maintaining resource isolation. |
| CR-690 | MUST | ✅ | **Adaptive Ridge Reloading**: The backtest engine MUST automatically detect high-Sharpe windows (>10.0) and iteratively reload Ridge shrinkage intensity (up to 0.50) to enforce weight diversity. |
| CR-691 | MUST | ✅ | **Numerical Clipping**: realize daily returns MUST be clipped at [-100%, +100%] in the meta-aggregation layer to prevent mathematical divergence in covariance estimation. |
| CR-200 | MUST | ✅ | **Deep Forensic Reporting**: Every tournament must generate a human-readable \"Deep Forensic Report\" tracing the Five-Stage Funnel and providing window-by-window portfolio snapshots. |



---

**Status**: ✅ All requirements satisfied, validated and hardened for Q1 2026 Production.
