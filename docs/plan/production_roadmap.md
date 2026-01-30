# Production Roadmap: 2026 Quantitative Outlook

This roadmap outlines the strategic development goals for the TradingView Scraper quantitative platform for 2026, focusing on alpha expansion, execution intelligence, and institutional resilience.

## Q1 2026: Execution Intelligence & Churn Optimization (COMPLETED)

### 1. Advanced Rebalancing Logic
- **Drift-Aware Execution**: Upgraded `drift-monitor` with Partial Rebalancing and Order Generation.
- **Turnover Penalties**: Implemented L1-norm penalty in Custom Optimizer.
- **XS Momentum**: Transitioned to robust global percentile ranking.
- **Spectral Regimes**: Integrated `TURBULENT` state detection and Barbell scaling.

### 2. Immutable Audit & Reproducibility
- **Decision Ledger 2.0**: **COMPLETED**. Implemented `audit.jsonl` with cryptographic chaining (SHA-256), environment pinning (`uv.lock`), and Git provenance.
- **Data Hashing**: Implemented deterministic `df_hash` for verifiable data lineage.
- **Audit Orchestration**: Updated `run_production_pipeline.py` to wrap steps in audit blocks.
- **Integrity Verification**: Created prototype `replay_backtest.py` to verify and reconstruct historical decisions.

## Q2 2026: Hierarchical Intelligence & Strategy Expansion (PLANNED)

### 1. Unified Hierarchical Intelligence
- **Cluster-Aware Selection**: Implement dynamic `Top N` per cluster based on cluster variance.
- **Linkage Synchronization**: Unify distance metrics and linkage methods across selection, backtesting, and optimization.
- **HERC Exploration**: Research Hierarchical Equal Risk Contribution (HERC) using CVaR as the primary risk measure.

### 2. Relative Value & XS Momentum (COMPLETED)
- **Cross-Sectional (XS) Momentum**: Implemented percentile-based ranking in `natural_selection.py`.
- **Sector Rotation Engine**: Propagated sector metadata to the pruning layer.

### 3. Short Mean Reversion
- **Selling Rips**: Develop specialized configurations for identifying overbought assets within confirmed downtrends across Equities, Forex, and Crypto.

## Q3 2026: Spectral Intelligence & Regime Detection

### 1. Wavelet-Based Regime Detection
- **Spectral Turbulence**: Fully integrate Discrete Wavelet Transform (DWT) entropy metrics into the `MarketRegimeDetector` to identify non-stationary volatility shifts before they manifest in standard deviation metrics.
- **Regime-Specific Presets**: Create automated manifest profiles that trigger specialized constraints (e.g., tighter cluster caps) during `CRISIS` regimes.

## Q4 2026: Institutional Infrastructure

### 1. Manifest-Driven Orchestration
- **Universal Runner**: Replace remaining bash-based scan lists with a centralized manifest runner that supports concurrent execution, automated retries, and unified run-scoped logging.
- **Metadata Parity 2.0**: Implement real-time parity checking between the offline symbols catalog and TradingView's live data to prevent point-in-time mapping errors.

## Ongoing Maintenance
- **Data Resilience**: Continuous improvement of the self-healing `make data-repair` loop.
- **Optimizer Benchmarking**: Monthly "Tournament" runs to evaluate if third-party engines (`skfolio`, `Riskfolio`) are outperforming the `Custom` convex engine in realized Sharpe stability.

## Phase 4: Engine Migration & Simulator Repair (COMPLETED - Jan 2026)

### 1. Engine Migration (Sync to Standards)
- **Status**: **COMPLETED**.
- **Outcome**: All engines (`custom`, `skfolio`, `riskfolio`, `cvxportfolio`) now support the standardized `benchmark` (Hierarchical Equal Weight) profile.
- **Regularization**: Enforced L2 regularization across all optimization wrappers to stabilize "Ghost Alpha".

### 2. Simulator Diagnostic (VectorBT)
- **Status**: **RESOLVED**.
- **Outcome**: Fixed signal alignment and return calculation (Day 0 fix). Harmonized rebalance modes across `custom`, `cvxportfolio`, and `vectorbt`.
- **Fidelity**: Achieved perfect parity between institutional simulators for window-drift modeling.

## Phase 7: Macro-Aware Intelligence (Jan 2026)

### 1. Structural & Markovian Regime Detection
- **Status**: **COMPLETED**.
- **Outcome**: Integrated Hurst Exponent, ADF Test, and 2-State Gaussian HMM into the `MarketRegimeDetector`.

### 2. Generalized All Weather Model
- **Status**: **COMPLETED**.
- **Outcome**: Implemented two-axis quadrant detection (Growth vs. Stress) to classify institutional market environments (`EXPANSION`, `STAGNATION`, etc.).

### 3. Quadrant-Aware Optimization
- **Status**: **COMPLETED** (Jan 2026).
- **Outcome**: Implemented `AdaptiveMetaEngine` which dynamically switches profiles (Max Sharpe, Barbell, MinVar, HRP) based on the detected All Weather quadrant. Validated risk reduction (sub-1% volatility) in initial tournaments.

## Phase 8: Bayesian Intelligence & Feedback Loops (COMPLETED - Jan 2026)

### 1. Bayesian Estimation (Black-Litterman)
- **Status**: **COMPLETED**.
- **Outcome**: Implemented `BlackLittermanEstimator` and regime-based view generation. Achieved measurable Sharpe gains in adaptive profiles.

### 2. Hierarchical Risk Parity 2.0 (HERC)
- **Status**: **COMPLETED**.
- **Outcome**: Standardized intra-cluster risk parity. Reduced structural risk across the entire tree by 34%.

## Phase 11: Production Certification & Scale-Up (COMPLETED - Jan 2026)

### 1. Binance Ratings Certification
- **Status**: **COMPLETED** (2026-01-16).
- **Outcome**: Validated "Rating All" (Long/Short) profiles.
- **Key Metrics**: 
    - **Short Profile**: 1.65 Sharpe, -6.17% MaxDD.
    - **Long Profile**: 1.49 Sharpe, -8.68% MaxDD.
- **Infrastructure**: Certified "DataOps v2" (Superset) and "Backtest Engine v2" (Turnover Fix).

### 2. Execution Intelligence
- **Status**: **IN PROGRESS**.
- **Traceability**: Implemented `implementation_alternatives` metadata to map Spot Analysis -> Perp Execution.
- **Next Step**: Integrate with `Nautilus` OMS for live paper trading.

## Phase 12: Feedback-Driven Calibration (PLANNED - Q2 2026)

Now that the Bayesian framework is in place, the focus shifts to closing the loop between realized performance and parameter selection.

### 1. The Threshold Auditor
- **Goal**: Automate the optimization of regime detector thresholds.
- **Action**: Develop a "Regime Regret" metric to quantify the cost of incorrect profile switches and adjust `crisis_threshold` dynamically.

### 2. Bayesian Shrinkage (Dynamic)
- **Goal**: Move from static Ledoit-Wolf to regime-aware shrinkage.
- **Action**: Adjust the shrinkage intensity ($\\tau$) based on market turbulence to further robustify covariance estimates.

### 3. Execution Shortfall Feedback
- **Goal**: Adjust transaction cost models based on realized slippage from high-fidelity simulators (CVX/Nautilus).
- **Action**: Implement a feedback loop that updates `backtest_slippage` parameters in the manifest.

## Phase 9: Execution Intelligence & High-Fidelity Hardening (ACTIVE - Jan 2026)

Now that the foundation is calibrated and synchronized, the focus shifts to extracting alpha from the hierarchical structure and hardening the simulation fidelity.

### 1. Hierarchical Equal Risk Contribution (HERC)
- **Goal**: Transition from Hierarchical Equal Weight (current benchmark) to Hierarchical Risk Parity.
- **Action**: Implement cluster-level risk parity in `engines.py`, utilizing the `cluster_stats` already available in the universe.

### 2. Adaptive Regularization (Regime-Aware)
- **Goal**: Adjust optimization penalties based on market stress.
- **Action**: Scale the L2 `gamma` coefficient dynamically (e.g., 0.05 in `EXPANSION`, 0.15 in `CRISIS`) to further robustify portfolios against non-stationary regimes.

### 3. Nautilus Event-Driven Logic
- **Status**: **INTEGRATED (Alpha)**.
- **Goal**: Move beyond the high-fidelity bypass.
- **Action**: Implement the `NautilusRebalanceStrategy` and automated `DataCatalog` ingestion to provide true event-driven order execution simulation.

### 4. Transaction Cost Optimization (TCO)
- **Goal**: Minimize implementation shortfall using calibrated simulator data.
- **Action**: Implement "Execution Ranking" within clusters. Prioritize assets with higher `value_traded` and lower `realized_vol` to fill cluster allocations.
