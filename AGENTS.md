# AI Agent Guide: Quantitative Portfolio Platform

This document provides a comprehensive guide for AI agents working on the TradingView Scraper quantitative platform. It codifies the institutional workflows, risk engine logic, and implementation standards developed for multi-asset portfolio management.

## 1. The 3-Pillar Architecture
The platform is organized into three orthogonal pillars to ensure logical purity and numerical stability.

### Pillar 1: Universe Selection (Filtering)
- **Standard**: HTR v3.4.2 (Hierarchical Threshold Relaxation).
- **Goal**: Recruit a high-hygiene subset of assets with validated secular history.
- **Clustering**: Performed on raw asset returns to ensure factor diversity in the candidate pool.

### Pillar 2: Strategy Synthesis (Alpha Generation)
- **The Strategy Atom**: Smallest unit of alpha, defined as `(Asset, Logic)`. Each atom MUST have exactly ONE logic.
- **Synthetic Long Normalization**: SHORT return streams are inverted ($R_{syn} = -1 \times R_{raw}$) to ensure positive-alpha bias for solvers.
- **Composition**: Atoms can be ensembled into complex strategies (e.g., Long/Short pairs).

### Pillar 3: Portfolio Allocation (Risk Layer)
- **Decision-Naive Solvers**: Mathematical engines (`skfolio`, `riskfolio`) that optimize provided streams.
- **Synthetic Hierarchical Clustering**: Clustering is performed on *synthesized* return streams to identify logic-space correlations.
- **Constraint Delegation**: Targets like **Market Neutrality** are handled as native solver constraints ($|w^T\beta| \le 0.15$), ensuring global optimality across all atoms.

---

## 2. Configuration & Reproducibility

The platform uses a schema-validated JSON manifest system to ensure every run is perfectly reproducible.

### Workflow Profiles (configs/manifest.json)
- **`production`**: Institutional high-integrity settings (500d history, 252d train, 25% global caps, all optimizers enabled).
- **`canary`**: Early-access profile with **Feature Flags** enabled (Spectral Regimes, Decay Audit).
- **`development`**: Lightweight profile for fast iteration (60d history, 50 symbol limit).

### Feature Toggles (CLI Overrides)
For tactical runs, use environment variables or Makefile shortcuts instead of editing the manifest.

| Shortcut | Environment Variable | Purpose |
| :--- | :--- | :--- |
| `VETOES=1` | `TV_FEATURES__FEAT_PREDICTABILITY_VETOES=1` | Enable strict alpha-predictability filters. |
| `STRICT=1` | `TV_STRICT_HEALTH=1` | Veto any asset with even 1 missing bar. |
| `LOOKBACK=N` | `TV_LOOKBACK_DAYS=N` | Override secular history depth. |

### Execution
Agents should prioritize namespace-prefixed targets:
```bash
make flow-production PROFILE=production
```

### Logging & Visibility
Every step of the production sequence persists its full execution trace in the run directory:
- **Log Path**: `data/artifacts/summaries/runs/<RUN_ID>/logs/`
- **Real-time Progress**: The orchestrator parses log output to provide dynamic progress bars for long-running tasks.
- **Traceability**: All log paths are recorded in the `audit.jsonl` ledger for each step.

---

## 5. Key Developer Commands

| Command | Namespace | Purpose |
| :--- | :--- | :--- |
| `make flow-production` | **Flow** | Full institutional production lifecycle (Vectorized Simulators). |
| `make flow-prelive` | **Flow** | High-fidelity pre-live verification (includes Nautilus). |
| `make flow-dev` | **Flow** | Fast-path development execution. |
| `make scan-run` | **Scan** | Execute composed discovery scanners. |
| `make data-fetch` | **Data** | Ingest historical market data. |
| `make data-repair` | **Data** | High-intensity gap repair for degraded assets. |
| `make data-audit` | **Data** | Session-Aware health check. |
| `make research-persistence` | **Data** | Research trend and mean-reversion persistent duration. |
| `make port-optimize` | **Port** | Strategic asset allocation (Convex). |
| `make port-test` | **Port** | Execute 3D benchmarking tournament. |
| `make port-report` | **Port** | Generate unified quant reports. |
| `make report-sync` | **Report** | Synchronize artifacts to Gist. |
| `make clean-all` | **Clean** | Wipe all data, exports, and summaries. |
| `make clean-archive` | **Clean** | Archive old runs (keep 10) to `data/artifacts/archive`. |
| `make check-archive` | **Clean** | Dry-run archive to preview deletions. |


---

### 6. Strategic Guiding Principles for Agents
1.  **Alpha must survive friction**: Prioritize optimization engines that maintain Sharpe ratio stability in high-fidelity simulation. Use `feat_turnover_penalty` to minimize churn.
2.  **Spectral Intelligence**: Prioritize spectral (DWT) and entropy metrics for regime detection over simple volatility ratios. Use `feat_spectral_regimes` for adaptive scaling.
3.  **HTR Resilience**: Always utilize the **Hierarchical Threshold Relaxation (v3.3)** loop to prevent winner sparsity. Verify recruitment stages in `audit.jsonl` if solver failure occurs.
4.  **Execution Integrity**: Use `feat_partial_rebalance` to avoid noisy small trades. Generate implementation orders via `scripts/track_portfolio_state.py --orders`.
4.  **TDD & Feature Flags**: All new risk management features must be implemented via TDD and gated behind feature flags in `TradingViewScraperSettings` to ensure production stability.
5.  **Provenance First**: Always verify that the `manifest.json` has been archived in the run directory.
6.  **Audit Integrity**: Every production decision must be backed by an entry in the `audit.jsonl` ledger. Never bypass the audit chain for manual weight overrides.
7.  **No Padding**: Ensure the returns matrix preserves real trading calendars; never zero-fill weekends for TradFi assets.

---

## 7. Selection Standards (The Alpha Core)

The platform supports multiple selection architectures, evaluated via head-to-head tournaments.

### Current Standards
- **Selection v3.4 (Stabilized HTR Standard)**: **Hierarchical Threshold Relaxation**.
    - Integrates the 4-stage relaxation loop (Strict -> Spectral -> Cluster Floor -> Alpha Fallback).
    - **Numerical Hardening**: Implements **Dynamic Ridge Scaling** (Iterative shrinkage) to bound Kappa < 5000.
    - **Adaptive Resilience**: Default fallback to **ERC (Equal Risk Contribution)** safety profile.
    - Ensures $N \ge 15$ candidates and stable convex optimization.
- **Selection v3.2 (Log-MPS Core)**: Deep Audit Standard using additive log-probabilities.
- **Selection v2.1 (Stability Anchor)**: **Additive Rank-Sum (CARS 2.1)**. 
    - Uses **Multi-Method Normalization** (Logistic/Z-score/Rank).
    - Optimized for lower volatility and maximum drawdown protection.
- **Selection v3.1 (Legacy Alpha)**: Original Multiplicative Standard.

### Guiding Rule
Always prefer **Selection v3.2** for maximum alpha and regime-aware robustness. Use **Selection v2.1** for conservative "Core" profiles where drawdown minimization is the primary objective.


---

## 8. Crypto Sleeve Operations

The crypto sleeve operates as an orthogonal capital allocation within the multi-sleeve meta-portfolio architecture.

### Exchange Strategy
- **Production**: BINANCE-only for institutional crypto sleeve (highest liquidity, cleanest execution).
- **Research**: Multi-exchange (BINANCE/OKX/BYBIT/BITGET) configs available for experimentation.

### Key Commands
| Command | Purpose |
| :--- | :--- |
| `make flow-production PROFILE=crypto_production` | Full crypto-only production run |
| `make scan-run PROFILE=crypto_production` | Execute crypto discovery scanners |
| `make flow-meta-production` | Multi-sleeve run including crypto |

### Crypto-Specific Parameters
| Parameter | Crypto Value | TradFi Value | Rationale |
| :--- | :--- | :--- | :--- |
| `entropy_max_threshold` | 0.999 | 0.995 | Higher noise tolerance for microstructure |
| `backtest_slippage` | 0.001 | 0.0005 | Higher volatility and wider spreads |
| `backtest_commission` | 0.0004 | 0.0001 | Typical CEX maker/taker fees |
| `feat_dynamic_selection` | false | true | Stable universe benefits crypto |

### Calendar Handling
- Crypto uses XCRY calendar (24x7, no holidays).
- When joining with TradFi sleeves in meta-portfolio, use **inner join** on dates.
- **Never zero-fill weekends** for crypto-TradFi correlation calculations.

### Production Pillars (Forensic Standards)
Agents must ensure every production run adheres to the following five pillars:
1.  **Regime Alignment**: The `step_size` must be **10 days (Bi-Weekly)** for crypto production to capture fast-moving volatility clusters. (Updated Jan 2026).
2.  **Tail-Risk Mitigation**: Forensic validation proves that 20-day alignment provides the best balance between momentum capture and drawdown protection (-15.1% MaxDD). **Annualized Return Clipping (-99.99%)** is enforced to prevent mathematical divergence in high-drawdown scenarios.
3.  **Alpha Capture**: High-resolution factor isolation (threshold=0.45) and **Entropy Resolution (Order=5)** ensure winners are orthogonal and high-conviction. **Selection Scarcity Protocol (SSP)** ensures robust multi-stage fallbacks (Max-Sharpe -> Min-Var -> EW) when the winner pool is sparse.
4.  **Directional Purity**: SHORT candidate returns must be inverted ($R_{synthetic} = -1 \times R_{raw}$) before optimization to ensure risk-parity engines (HRP/MinVar) correctly reward stable downward drift.
5.  **Toxic Data Guard**: Assets with daily returns > 500% (5.0) are automatically dropped to prevent optimizer corruption. Synthetic shorts are capped at -100% loss.

### 9. Numerical Stability & Reporting
 1.  **Stable Sum Gate**: Mixed-direction or Short-only portfolios MUST use the Stable Sum Gate in rebalance simulations to prevent division-by-near-zero return artifacts ($W_{sum} < 1e-6$).
 2.  **SSP Minimums**: Selection pipelines MUST enforce a 15-winner floor (SSP) to ensure optimizer rank stability and prevent profile convergence.
 3.  **Reporting Purity**: Reporting scripts must be "Identity-Aware" and defensive, utilizing `.get()` for all metadata lookups and restructuring flat tournament data into nested hierarchies for stable Markdown generation.
 
## 10. Observability & Compute Resilience
 1.  **Trace Everything**: Every pipeline stage and parallel task MUST be wrapped in an OpenTelemetry span. Use the `@trace_span` decorator for automatic instrumentation.
 2.  **Deterministic Lifecycle**: Always use the `with RayComputeEngine() as engine` context manager pattern to ensure the Ray cluster is gracefully shut down.
 3.  **Structured Logging**: Prefer the `get_telemetry_logger()` factory to ensure all logs are injected with `trace_id` and `span_id` for cross-node correlation.
 4.  **Resource Limits**: Parallel execution must respect `TV_ORCH_CPUS` and `TV_ORCH_MEM_GB` to prevent system-wide resource contention.

## 11. Claude Skills
The platform provides a set of Claude Code skills for high-level interaction.

| Skill | Purpose | Example |
| :--- | :--- | :--- |
| `/quant-select` | Run selection pipeline | `/quant-select crypto_long` |
| `/quant-backtest` | Run historical simulation | `/quant-backtest 20260121_143022` |
| `/quant-discover` | Discover candidate assets | `/quant-discover binance_spot` |
| `/quant-optimize` | Run portfolio optimization | `/quant-optimize 20260121_143022` |

These skills leverage the `QuantSDK` and `StageRegistry` for deterministic execution.
