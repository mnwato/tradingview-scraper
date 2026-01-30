# Design Document: MLOps-Centric Selection Pipeline (v4)

## 1. Objective
Refactor the quantitative selection logic into a formal, stage-based inference pipeline inspired by MLOps and modern Data Engineering practices. This architecture prioritizes statelessness, observability, and modularity, allowing for rapid experimentation with new alpha factors and scoring models.

## 2. The Universal Pipeline Architecture
The v4 pipeline is defined as a sequence of discrete, swappable **Stateless Transformers**. Each stage consumes a validated `SelectionContext` and returns an enriched version of it.

### 2.1 Mapping Selection to Pipeline Stages
| Stage | Pipeline Component | Responsibility |
| :--- | :--- | :--- |
| **Ingestion** | `DiscoveryProvider` | Fetch raw assets/metadata from Lakehouse (L4 Scanners). |
| **Feature Engineering** | `FeatureGenerator` | Calculate alpha factors (Momentum, ADX, Entropy, etc.). |
| **Inference** | `ConvictionScorer` | Apply scoring models (Log-MPS, ML models) to produce conviction. |
| **Partitioning** | `FactorBucketizer` | Unsupervised grouping of assets into orthogonal factor groups. |
| **Policy** | `SelectionController` | Pruning logic (HTR Loop, Top-N recruitment). |
| **Synthesis** | `StrategySynthesizer` | Generating the final `StrategyAtom` manifest for Allocation. |

## 3. Data Contracts & Schema Enforcement
To ensure 100% reproducibility and prevent hidden state bugs, every stage transition is validated by strict data models (Pydantic).

### 3.1 `SelectionContext` (The State Container)
- `raw_pool`: Initial list of candidates with discovery metadata.
- `feature_store`: DataFrame containing calculated technical/statistical features.
- `inference_outputs`: Probability scores and model-specific metadata.
- `clusters`: Mapping of assets to identified factor buckets.
- `winners`: The final subset of recruited strategy atoms.

## 4. Logical Separation (The "Shadow Pipeline")
The v4 pipeline will reside in a parallel namespace to ensure the existing `v3.4` production path remains untouched.

- **Namespace**: `tradingview_scraper.pipelines.selection.*`
- **Isolation**: v4 components MUST NOT import from `selection_engines.impl.*`.
- **Parity Goal**: The `Log-MPS` transformer in v4 must produce bit-identical results to the `v3.4` engine during the transition phase.

## 5. MLOps Capabilities

### 5.1 Champion/Challenger Framework
The pipeline supports running multiple `ConvictionScorer` implementations in a single run, tagging outputs for easy performance comparison.

### 5.2 Observability & Traceability
Every run generates an `audit.jsonl` that follows the standard ML tracking schema:
- **Inputs**: Data version (Git hash + Data hash).
- **Parameters**: Hyperparameters for HTR (Entropy ceiling, ADX floor).
- **Metrics**: Cluster density, average conviction, pool diversity.
- **Artifacts**: Link to the generated `portfolio_candidates.json`.

### 5.3 Global Ledger Mapping
To maintain schema hygiene, the v4 pipeline's internal audit trail is mapped to the `data.pipeline_audit` field of the global system ledger. This ensures that MLOps stage transitions are traceable without bloating the high-frequency metrics namespace used for performance analysis.

### 5.4 Matrix Stability Validation
The v4 pipeline has been validated across a multi-dimensional risk matrix (MaxSharpe, HRP, Barbell, MinVariance) using the `SelectionPipelineAdapter`. This ensures that the modular HTR loop correctly provides a stable pool of strategy atoms to all production portfolio engines.

### 5.5 Grand Tournament Standard (v3.4.6)
Institutional validation now requires a head-to-head tournament against the `v3.4` champion engine. Success criteria include:
- **Zero Bankruptcy**: 100% survival across all stress windows.
- **Telemetry Purity**: Verifiable structured events in `data.pipeline_audit`.
- **Logic Preservation**: Match legacy alpha signatures while improving modularity.

## 6. System Coexistence & Benchmarking
To ensure long-term statistical integrity, v4 is designed to coexist with legacy engines.
- **Legacy Preservation**: Files in `selection_engines/impl/v3_*.py` are frozen to serve as immutable benchmarks.
- **Versioning**: Tournament logs must explicitly tag the `spec_version` (e.g., `4.0-mlops` vs `3.4`) to prevent cross-contamination in meta-analysis.

## 7. Statistical Grand Tournament Protocol
To identify pipeline bottlenecks and alpha decay thresholds, the system implements a multi-dimensional sweep:
- **Spatial Diversity**: Comparison of $v3$ vs $v4$ selection engines.
- **Temporal Frequency**: Testing of `step_size` sensitivity ($5d, 20d, 60d$).
- **Memory Depth**: Evaluation of `train_window` impact on regime stability.
- **Factor Sensitivity**: Audit of `feature_lookback` consistency across varying volatility regimes.
The outcome of this protocol is a **Bootstrap-validated Performance Matrix** ensuring results are not due to window-selection bias.

### 9.1 High-Entropy Hardening (CR-490)
To mitigate the "flash-crash" instability observed in Windows 140/300, the `SelectionPipeline` implements **Entropy-Aware Hardening**:
- **Trigger**: System-wide mean entropy $> 0.95$.
- **Action**: Tighten `entropy_max_threshold` by 10% and increase `default_shrinkage_intensity` (Ridge loading) to stabilize the covariance matrix.
- **Goal**: Prioritize low-noise factor anchors when statistical confidence in high-alpha assets is degraded.

## 6. Implementation Strategy (The HTR Controller)
The **Hierarchical Threshold Relaxation (HTR)** logic is moved from recursion into a **Pipeline Orchestrator**.

### 6.1 `SelectionPipeline` (Orchestrator)
A high-level controller that manages the stage execution graph and HTR loop.

**Logic Flow:**
1.  **Initialize**: Load data (Stage 1) and calculate features (Stage 2). This is done ONCE.
2.  **Loop (HTR Stages 1-4)**:
    *   Set `SelectionContext.params` for current stage (e.g., `relaxation_stage=1`).
    *   Execute **Inference** (Stage 3).
    *   Execute **Partitioning** (Stage 4).
    *   Execute **Policy** (Stage 5).
    *   **Check**: If `len(winners) >= 15`, break loop.
3.  **Finalize**: Execute **Synthesis** (Stage 6).

### 6.2 `SelectionPolicyStage` (Stage 5)
Responsible for the *single-pass* recruitment logic:
- Apply hard vetoes (Entropy, Efficiency, Metadata).
- Rank candidates by `alpha_score` within each cluster.
- Select Top-N per cluster.
- Handle "Representative Forcing" if `relaxation_stage >= 3`.
- Handle "Balanced Fallback" if `relaxation_stage >= 4`.

## 10. Vectorized Probability Mapping (CR-530)
To support institutional scaling ($N > 1000$), the `AlphaScorer` utilizes vectorized probability mapping:
- **Broadcasting**: Normalization methods (CDF, Z-Score) are applied across the entire feature matrix in a single `numpy` operation.
- **Complexity**: Reduces selection latency from $O(N)$ to $O(1)$ effectively, ensuring real-time responsiveness even with massive candidate pools.

## 11. Sector-Aware Diversification (CR-540)
The `SelectionPolicyStage` utilizes discovery metadata to enforce sector-level limits:
- **Constraint**: No single sector can exceed 40% of the recruited winner pool.
- **Implementation**: The HTR loop prunes low-conviction assets within over-concentrated sectors during recruitment, ensuring the final portfolio remains uncorrelated across different industry verticals.

## 12. Bounded Cluster Resolution (CR-650)
The Partitioning stage (Stage 4) is the bridge between Alpha and Risk. To prevent "Factor Over-Fitting" and ensure stable risk budgeting:
- **Constraint**: A hard ceiling of **25 clusters** is enforced for all production sleeves.
- **Rationale**: Prevents idiosyncratic noise from creating single-asset clusters, ensuring that branch variance calculations in HRP/MinVar engines are statistically significant.
- **Fallback**: If the distance threshold (0.7) generates $> 25$ clusters, the engine automatically switches to `maxclust` pruning to reach the institutional target.

## 13. Advanced Allocation Strategies (Pillar 3)

### 13.1 Market Neutral as a Constraint (CR-570)
In the v4 architecture, Market Neutrality is decoupled from Alpha Generation. 
- **Mechanism**: The Portfolio Engine applies a linear constraint on the portfolio beta relative to a benchmark (e.g., BTC or SPY).
- **Benefit**: Allows the solver to select the most "alpha-dense" atoms while maintaining a neutral footprint, avoiding the liquidity-constrained bottleneck of manual pair-trading.

### 13.2 Barbell Antifragility Mapping (CR-580)
The `barbell` strategy segments capital into "Core" (Antifragile) and "Aggressor" (High-Conviction) layers.
- **Synthesis Mapping**: Because optimization happens in "Strategy Space" (Atoms), the engine explicitly maps Strategy IDs (e.g., `BTC_mom_LONG`) back to physical stats (e.g., `BTC` Antifragility Score) to ensure the Core layer truly contains the most resilient assets.

### 13.3 Hardened Simulation Bounds (CR-660)
To prevent mathematical drift in high-volatility regimes:
- **Liquidation Floor**: If Window MaxDD reaches -100%, the strategy is marked as "Liquidated" and subsequent returns for that run are locked at 0.
- **TWR Normalization**: The `stable_institutional_audit.py` script utilizes Time-Weighted Return (TWR) compounding to provide a realistic benchmark of the investor experience across sequential rebalances.

## 14. Final Operational Certification (v3.6.1)
As of Q1 2026, the v4 Selection Pipeline is the **Institutional Standard** for the multi-sleeve meta-portfolio.
- **Reliability**: Validated via exhaustive 3D Matrix Tournament (Selection x Profile x Engine).
- **Hardened Allocation**: Enforced mandatory 25% max cluster weight (CR-590) and bounded resolution (CR-650).
- **Directionality**: 100% verified SHORT atom normalization.
- **Traceability**: All stage transitions audited via `comprehensive_audit_v4.py`.
- **Statistical Benchmark**: Achieved Mean Sharpe 5.48 with 60/20/20 configuration.

## 15. Deep Forensic Audit Methodology (v3.6.1)
Institutional verification is now standardized via automated per-window trace:
- **Directional Trace**: Verifies sign preservation across thousands of strategy atom implementations.
- **Volatility Anchors**: Ensures profiles remain within their risk bands (MinVar: 0.35, HRP: 0.45, MaxSharpe: 0.90).
- **Outlier Quarantine**: Automated identification of "Flash Crash" windows to trigger safety protocols.
- **Funnel Trace**: Traces candidates from Discovery (N=110) to Selection (N=20) to ensure high-conviction recruitment.

## 17. Risk Profile Benchmarks & Volatility Bands
To ensure behavioral consistency across different market regimes, the system enforces target volatility bands for each risk profile:

| Profile | Target Volatility | Behavioral Standard |
| :--- | :--- | :--- |
| **MinVar / MarketNeutral** | **0.35** | Conservative, focused on capital preservation and beta minimization. |
| **HRP / Risk Parity** | **0.45 - 0.50** | Balanced, focused on equalizing risk contribution across factor clusters. |
| **Equal Weight** | **0.60** | Baseline, accepting full system variance from the selected pool. |
| **Max Sharpe** | **0.90** | Aggressive, maximizing risk-adjusted return through factor concentration. |

### 17.1 Volatility Drift (Anomalies)
The `stable_institutional_audit.py` script automatically monitors realized volatility against these benchmarks. Significant deviations (> 0.25) are flagged as "DRIFT" anomalies, usually indicating a failure of the covariance estimator or extreme asset-level variance.

## 19. Strategic Risk Delegation (CR-640)
To maintain the logical purity of the 3-Pillar architecture, strategic constraints like **Directional Balance** (LONG/SHORT exposure caps) are delegated to **Pillar 3 (Allocation)**:
- **Pillar 1 (Selection)**: Focuses on alpha conviction and asset-level statistical hygiene (Kurtosis, Volatility).
- **Pillar 3 (Allocation)**: Enforces portfolio-level risk policy. Strategies requiring balance (e.g., Market Neutral) implement directional caps as explicit solver constraints.
- **Benefit**: Prevents the alpha funnel from prematurely pruning high-conviction signals based on arbitrary global limits, allowing for more flexible strategy-specific risk management.

## 20. Tail-Risk Mitigation (CR-630)
The v4 pipeline integrates high-order statistical moments and hard volatility caps:
- **Fat-Tail Veto**: Hard veto for assets with **Kurtosis > 20**, identifying extreme "jump-risk" candidates.
- **Volatility Hard-Cap**: Assets exceeding **250% annualized volatility** are automatically vetoed (CR-631).
- **CVaR Penalization**: Assets with extreme Conditional Value at Risk are down-weighted in the Log-MPS scoring logic to prioritize stable alpha.

## 21. Forensic Verification & Metric Purity (CR-750)
To ensure the mathematical integrity of the realization layer, the pipeline implements a post-simulation verification stage:
- **Raw Return Audit**: Simulation results are cross-checked against raw daily returns logged in the `audit.jsonl` ledger.
- **Metric Agreement**: Sharpe and MaxDD are independently re-calculated using standard geometric mean and high-water-mark algorithms to detect backend simulator drift.
- **Geometric Baseline**: Annualized returns are anchored to Compound Annual Growth Rate (CAGR) standards to eliminate arithmetic inflation artifacts.

## 24. Strategy as an Asset & Meta-Allocation (v3.8.2 Update)
As of v3.8.2, the platform implements a fractal optimization architecture where individual strategy outputs are treated as synthetic asset classes:

- **Granular Strategy Profiles**: Targeted profiles (e.g., `crypto_rating_all`, `crypto_rating_ma`) generate isolated equity curves for specific alpha logics.
- **Decoupled Persistence**: Strategy-level return streams are persisted as standalone `.pkl` files, enabling meta-portfolio aggregation without re-running the underlying simulations.
- **Fractal Optimization**: The Pillar 4 Meta-Allocation engine applies risk profiles (e.g., HRP) across these synthetic strategy assets to construct a global Meta-Portfolio.
- **Metric Alignment**: Annualization factors are standardized (365 for crypto sleeves) across the entire stack, ensuring consistent Sharpe and Volatility benchmarks from asset-level to meta-portfolio level.
- **Directional Modularity**: The system explicitly supports the generation of "Directional Alpha" return streams (Pure LONG or Pure SHORT). This modularity allows the Meta-Portfolio engine to balance overall exposure by treating a SHORT-only strategy as an asset that provides negative beta exposure.

## 26. The Atom Identity Standard (CR-823)
To support multi-strategy allocation across the same physical asset, the system utilizes a canonical **Atom ID** for all internal operations.
- **Format**: `{Symbol}_{Logic}_{Direction}` (e.g., `BINANCE:BTCUSDT_rating_ma_LONG`).
- **Persistence**: This ID is the primary key in the `returns_matrix.parquet` and `portfolio_returns.pkl`.
- **Mapping Logic**: Scripts (e.g., `correlation_report.py`) must be "Atom-Aware" and resolve physical symbols back to their corresponding Atom IDs using discovery metadata.

## 27. Metadata Hygiene & Null Logic Handling
To ensure valid atom generation, the system enforces a strict "Truth or Trend" logic fallback:
- **Rule**: If `logic` or `direction` is missing or explicitly `null` in metadata, it must be normalized to `trend` and `LONG` respectively.
- **Implementation**: `meta.get('logic') or 'trend'` ensures that falsy values (None, "") are correctly handled, preventing the generation of corrupted keys like `Asset_None_Direction`.

## 29. Selection Scarcity Protocol (SSP)
To prevent mathematical degeneration in Pillar 3 Portfolio Engines (where HRP/MinVar/MaxSharpe collapse into identical results), the system enforces a strict **Winner Floor**.
- **Requirement**: The v4 Selection Pipeline MUST recruit a minimum of **15 strategy atoms** for any production window.
- **Enforcement**: If the `relaxation_stage` reaches 4 and `len(winners) < 15`, the pipeline triggers an **Absolute Scarcity Fallback**, ignoring non-metadata vetoes (Entropy, ROC) until the floor is met.
- **Throughput Constraint**: If the total discovered pool (Ingestion) is less than 15, the SSP recruits the entire eligible universe. In these "Ultra-Sparse" scenarios ($N < 5$), profile convergence is expected and solvers will prioritize survival over optimization gain.

## 30. Anomaly Detection: Portfolio Convergence
A "Convergence Anomaly" occurs when distinct risk profiles produce identical weight distributions ($r > 0.999$).
- **Detection**: The `audit_ledger_anomalies.py` utility flags windows where HRP and Max Sharpe produce identical weight vectors.
- **Remediation**: Convergence is treated as a "Sparsity Warning." If persistent, the `top_n` or discovery liquidity floors must be relaxed.

## 38. High-Fidelity Simulation: Physical Normalization (CR-832)
To maintain compatibility with institutional execution engines (e.g., NautilusTrader), the simulation layer enforces a **Physical Normalization** standard.
- **Constraint**: Execution engines often have strict regular expression guards for symbol formats, which typically disallow metadata-augmented strings like logical Atom IDs (`Asset_Logic_Direction`).
- **Standard**: Before initiating a high-fidelity simulation or generating trade orders, all logical atoms MUST be flattened into their physical constituent assets.
- **Consolidation Logic**:
    - **Weights**: Sum the target weights of all atoms sharing the same `physical_symbol`.
    - **Returns**: Utilize the returns series of the physical asset (which is shared across its logical atoms).
- **Rationale**: This ensures the simulator acts upon tradeable exchange instruments while preserving the net intended exposure of the multi-strategy portfolio.

