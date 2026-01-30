# Requirements v3: Quantitative Portfolio Platform

## 1. The 3-Pillar Architecture
The platform is organized into three orthogonal pillars to ensure logical purity and numerical stability.

### Pillar 1: Universe Selection (Filtering)
- **Standard**: HTR v3.4.2 (Hierarchical Threshold Relaxation).
- **Goal**: Recruit a high-hygiene subset of assets with validated secular history.
- **Clustering**: Performed on raw asset returns to ensure factor diversity in the candidate pool.
- **Filtering Logic**:
    - **Strict Health**: Assets must meet strict data availability requirements.
    - **Predictability Vetoes**: Optional strict alpha-predictability filters.

### Pillar 2: Strategy Synthesis (Alpha Generation)
- **The Strategy Atom**: Smallest unit of alpha, defined as `(Asset, Logic)`. Each atom MUST have exactly ONE logic.
- **Synthetic Long Normalization**: SHORT return streams are inverted to ensure positive-alpha bias for solvers:
  - $R_{syn,long} = R_{raw}$
  - $R_{syn,short} = -clip(R_{raw}, upper=1.0)$ (short loss cap at -100%)
- **Composition**: Atoms can be ensembled into complex strategies (e.g., Long/Short pairs).
- **Directional Purity**: Synthetic shorts are treated as distinct positive-alpha streams.

### Pillar 3: Portfolio Allocation (Risk Layer)
- **Decision-Naive Solvers**: Mathematical engines (`skfolio`, `riskfolio`) that optimize provided streams without "market views".
- **Synthetic Hierarchical Clustering**: Clustering is performed on *synthesized* return streams to identify logic-space correlations.
- **Constraint Delegation**: Targets like **Market Neutrality** are handled as native solver constraints ($|w^T\beta| \le 0.15$), ensuring global optimality.

### Pillar 4 (Meta): Fractal Ensembling (Meta-Allocation)
- **Atomic Sleeves as Inputs**: Meta portfolios treat completed sleeve runs as assets.
- **Directional Integrity Gate**: Mixed-direction meta workflows MUST enforce a Directional Correction “Sign Test” at the sleeve boundary before ensembling.
- **Run Artifact Contracts**: Atomic sleeves MUST be meta-eligible only if required artifacts exist and are reproducible (see `docs/design/atomic_sleeve_audit_contract_v1.md`).
- **Automation**: Atomic sleeve runs SHOULD be validated via `scripts/validate_atomic_run.py` before pinning into meta profiles.
- **Spec Reference**: `docs/specs/atomic_run_validation_v1.md`

## 2. Selection Standards (The Alpha Core)

### Selection v3.4 (Stabilized HTR Standard)
- **Hierarchical Threshold Relaxation**: 4-stage relaxation loop (Strict -> Spectral -> Cluster Floor -> Alpha Fallback).
- **Numerical Hardening**: **Dynamic Ridge Scaling** (Iterative shrinkage) to bound Kappa < 5000.
- **Adaptive Resilience**: Default fallback to **ERC (Equal Risk Contribution)** safety profile.
- **Constraints**: $N \ge 15$ candidates to ensure stable convex optimization.

### Selection v3.2 (Log-MPS Core)
- **Deep Audit Standard**: Uses additive log-probabilities.
- **Preferred for**: Maximum alpha and regime-aware robustness.

### Selection v2.1 (Stability Anchor)
- **Additive Rank-Sum (CARS 2.1)**.
- **Normalization**: Multi-Method (Logistic/Z-score/Rank).
- **Preferred for**: Conservative "Core" profiles where drawdown minimization is primary.

## 3. Strategic Principles
1.  **Alpha must survive friction**: Optimization engines must maintain Sharpe ratio stability in high-fidelity simulation (slippage/commission).
2.  **Spectral Intelligence**: Use spectral (DWT) and entropy metrics for regime detection.
3.  **HTR Resilience**: Always utilize the HTR loop to prevent winner sparsity.
4.  **Execution Integrity**: Use `feat_partial_rebalance` to avoid noisy small trades.
5.  **Audit Integrity**: Every production decision must be backed by an entry in the `audit.jsonl` ledger.
6.  **No Padding**: Ensure the returns matrix preserves real trading calendars.

## 4. Modular Pipeline Architecture (v3.5+)

### 4.1 Design Principles
1. **Extend, Don't Duplicate**: All new modules must extend existing patterns (`BasePipelineStage`, `SelectionContext`).
2. **Single Responsibility**: Each stage/filter/ranker performs exactly one transformation.
3. **Composability**: Pipelines are chains of stages; stages can be swapped/reordered.
4. **Fractal Design**: Meta-portfolios treat sleeves as assets (recursive application).
5. **Fail-Fast Gates**: Meta workflows MUST support deterministic preflight gates (e.g., the Directional Correction “Sign Test”) controlled by feature flags and persisted as run artifacts.
6. **Audit Trail**: Every stage logs to `context.audit_trail`.

### 4.2 Core Abstractions

| Abstraction | Location | Contract |
| :--- | :--- | :--- |
| `BasePipelineStage` | `pipelines/selection/base.py` | `execute(context) -> context` |
| `SelectionContext` | `pipelines/selection/base.py` | Pydantic model with staged data slots |
| `BaseSelectionEngine` | `selection_engines/base.py` | `select(returns, candidates, stats, request) -> SelectionResponse` |
| `BaseRiskEngine` | `portfolio_engines/base.py` | `optimize(returns, clusters, meta, stats, request) -> EngineResponse` |
| `BaseFilter` | `pipelines/selection/filters/base.py` | `apply(context) -> context` (vetoes candidates) |
| `BaseRanker` | `pipelines/selection/rankers/base.py` | `rank(candidates, returns, strategy) -> ranked_candidates` |

### 4.3 Pipeline Modules

#### A. Discovery Pipeline (`pipelines/discovery/`)
- **Purpose**: Source candidate assets from external data providers.
- **Interface**: `BaseDiscoveryScanner.discover(params) -> List[CandidateMetadata]`.
- **Implementations**: `binance.py`, `tradingview.py`.

#### B. Selection Pipeline (`pipelines/selection/`)
- **Purpose**: Filter, score, and cluster candidates for portfolio construction.
- **Orchestrator**: `SelectionPipeline` with HTR loop.
- **Stages**: Ingestion → Feature Engineering → Inference → Clustering → Policy → Synthesis.
- **Sub-modules**:
    - `stages/`: Transformation stages.
    - `rankers/`: Scoring algorithms (MPS, Signal, Regime).
    - `filters/`: Veto policies (Darwinian, Spectral, Friction).

#### C. Meta-Portfolio Pipeline (`pipelines/meta/`)
- **Purpose**: Aggregate atomic sleeves into a unified portfolio.
- **Context**: `MetaContext` (extends `SelectionContext` with sleeve-level data).
- **Stages**: Sleeve Execution → Aggregation → Meta-Optimization → Flattening.
- **Key Classes**:
    - `SleeveAggregator`: Builds meta-returns matrix from sleeve performance.
    - `WeightFlattener`: Projects meta-weights to individual asset weights.

### 4.4 MLOps/Quant Vocabulary

| Term | Definition |
| :--- | :--- |
| **Strategy Atom** | `(Asset, Logic)` - Smallest unit of alpha. |
| **Sleeve** | An atomic portfolio (e.g., "Crypto Long", "US Equities Short"). |
| **Meta-Portfolio** | A portfolio of sleeves, optimized using Risk Parity. |
| **HTR Loop** | Hierarchical Threshold Relaxation - 4-stage filter relaxation. |
| **Synthetic Long** | SHORT returns inverted to positive-alpha streams. |
| **Regime** | Market environment classification (CRISIS, EXPANSION, STAGNATION, NORMAL). |
| **Quadrant** | Combination of Regime + Volatility (e.g., INFLATIONARY_TREND). |

## 5. Orchestration Layer (v3.6+)

### 5.1 Architecture Layers
The platform uses a layered orchestration architecture for scalability and observability:

```
┌────────────────────────────────────────────────────────────┐
│                   CLAUDE SKILL LAYER                       │
│  Addressable stage invocation via CLI/SDK                  │
│  URI: quant://pipeline/stage?run_id=abc&profile=crypto     │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│               WORKFLOW ENGINE (Prefect/DBOS)               │
│  DAG orchestration, automatic retries, task caching        │
│  State persistence, scheduling, observability              │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                  COMPUTE ENGINE (Ray)                      │
│  Parallel execution across workers                         │
│  Actor isolation for sleeves                               │
│  Distributed compute for large universes                   │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                   STAGE LOGIC LAYER                        │
│  BasePipelineStage, BaseRiskEngine, BaseFilter             │
│  Pure business logic, no orchestration concerns            │
└────────────────────────────────────────────────────────────┘
```

### 5.2 Callable/Addressable Stages

Every stage is registered with a unique identifier and can be invoked independently:

| Stage ID | Module | Purpose |
| :--- | :--- | :--- |
| `selection.ingestion` | `pipelines/selection/stages/ingestion.py` | Load candidates and returns |
| `selection.features` | `pipelines/selection/stages/feature_engineering.py` | Compute technical features |
| `selection.inference` | `pipelines/selection/stages/inference.py` | MPS/Signal scoring |
| `selection.clustering` | `pipelines/selection/stages/clustering.py` | Hierarchical clustering |
| `selection.policy` | `pipelines/selection/stages/policy.py` | Apply filter chain |
| `selection.synthesis` | `pipelines/selection/stages/synthesis.py` | Create strategy atoms |
| `meta.aggregation` | `pipelines/meta/aggregator.py` | Build meta-returns matrix |
| `meta.optimization` | `pipelines/meta/optimizer.py` | Meta-level risk parity |
| `meta.flattening` | `pipelines/meta/flattener.py` | Project to atom weights |

### 5.3 Invocation Methods

#### A. CLI Invocation
```bash
# Run single stage
quant stage run selection.ingestion --run-id abc --param profile=crypto_long

# List available stages
quant stage list --tag selection

# Get stage schema
quant stage schema selection.ingestion
```

#### B. SDK Invocation (Python)
```python
from tradingview_scraper.orchestration.sdk import QuantSDK

# Run single stage
context = QuantSDK.run_stage(
    "selection.ingestion",
    params={"profile": "crypto_long"},
    run_id="abc"
)

# Run full pipeline
context = QuantSDK.run_pipeline(
    "selection.full",
    params={"profile": "crypto_long"}
)
```

#### C. Prefect Flow (Scheduled/Observable)
```python
from tradingview_scraper.orchestration.flows.selection_flow import selection_flow

# Run as Prefect flow with retries and observability
result = selection_flow(run_id="abc", profile="crypto_long")
```

### 5.4 Ray Compute Patterns

| Pattern | Use Case | Module |
| :--- | :--- | :--- |
| `@ray.remote` task | Parallel stage execution | `orchestration/compute.py` |
| `@ray.remote` actor | Isolated sleeve execution | `orchestration/sleeve_executor.py` |
| `RayTaskRunner` | Prefect + Ray integration | `orchestration/flows/meta_flow.py` |

### 5.5 Workflow Engine Options

| Engine | Complexity | Features | Use Case |
| :--- | :--- | :--- | :--- |
| **Prefect** | Medium | DAG, Retry, UI, Scheduling | Production workflows |
| **DBOS** | Low | Transactional, Lightweight | Simple pipelines |
| **Manual** | None | None | Development/Testing |

### 5.6 Claude Skill Integration

Skills follow the [Agent Skills](https://agentskills.io) open standard, which is portable across Claude Code, OpenCode, and other compatible agents.

**Key Insight**: Skills are **SKILL.md files**, not Python functions. They are Markdown instructions that Claude reads and follows.

#### Skill Structure
```
.claude/skills/quant-select/
├── SKILL.md                    # Instructions + frontmatter (required)
└── scripts/
    └── run_pipeline.py         # Executable script (optional)
```

#### Available Skills

| Skill | Purpose | Invocation |
| :--- | :--- | :--- |
| `quant-select` | Run HTR selection pipeline | `/quant-select crypto_long` |
| `quant-backtest` | Run historical simulation | `/quant-backtest <run_id>` |
| `quant-discover` | Discover candidate assets | `/quant-discover binance_spot` |
| `quant-optimize` | Run portfolio optimization | `/quant-optimize <run_id>` |

#### SKILL.md Format (Agent Skills Standard)

```markdown
---
name: quant-select                    # 1-64 chars, lowercase, hyphens
description: Run the selection...     # 1-1024 chars, when to use
compatibility: Claude Code
allowed-tools: Bash(python:*) Read
---

# Instructions for Claude to follow...
```

#### Progressive Disclosure

Skills use progressive disclosure to minimize context usage:
### 5.7 Compute Resilience & Resource Awareness
- **Dynamic Resource Capping**: The orchestrator must support environment-based resource limits (e.g. `TV_ORCH_CPUS`, `TV_ORCH_MEM_GB`) to prevent OOM in constrained environments.
- **Stateful Isolation**: Distributed workers (Ray Actors) utilize a mixed-symlink strategy to share massive datasets (Lakehouse) while maintaining isolated output environments.
- **Fail-Fast Protocols**: Parallel executions are subject to a 100% success gate; partial failures trigger immediate pipeline abortion to preserve meta-portfolio integrity.

---

## 6. Phase 370: Correctness Hardening (SDD + TDD)

This phase formalizes a set of **correctness invariants** that are foundational to audit integrity. These items are intentionally “boring”: they prevent silent drift and make the platform easier to reason about.

### 6.1 Settings Determinism Invariants
1. **No duplicate field names** in configuration models (Pydantic / Settings).
   - Rationale: duplicate declarations silently override earlier defaults and can create environment-dependent behavior.
2. **Single source of truth** for `features.selection_mode`.
   - Default MUST be stable and documented.
   - Manifest overrides MUST take precedence over code defaults.
   - Env overrides MUST take precedence over manifest.
3. **Path derivation** MUST not use hard-coded relative strings when a settings field exists.
   - Example: use `settings.export_dir` not `Path("export")`.

### 6.2 DataOps / Alpha Contract Invariants
1. **Discovery export path** MUST be `settings.export_dir / <RUN_ID>` (default `data/export/<RUN_ID>`).
2. **Ingestion lakehouse path** MUST be consistent end-to-end:
   - the writer (sync) and the validator (toxicity checks) MUST read/write the same `lakehouse_dir`.
3. **Alpha cycle is read-only** with respect to external network I/O:
   - Alpha pipelines MUST not call TradingView/CCXT/WebSocket endpoints.
   - DataOps is the only flow permitted to mutate the lakehouse.

### 6.3 Meta-Portfolio Contract Invariants
1. **No hard-coded manifest path usage** inside meta orchestration.
   - Meta must resolve the active manifest via settings (`TV_MANIFEST_PATH`) or explicit CLI arg.
2. **Meta reproducibility** requires deterministic sleeve resolution:
   - meta runs MUST persist the resolved sleeve list (including run IDs) used for aggregation.
3. **Meta joins** must be calendar-safe:
   - crypto↔tradfi aggregation uses **inner join** on dates; never zero-fill calendar gaps.

### 6.4 Discovery Schema / Identity Invariants
1. `CandidateMetadata.identity` MUST be exactly `EXCHANGE:SYMBOL` (single prefix).
2. Discovery scanners MUST accept a structured params object (dict) with at least:
   - `config_path` (scanner config path)
   - `interval` (optional)
   - `strategy` / `logic` tag (optional)

---

## 7. Pipeline Audit Remediation Phases (371–374)

These phases are the next steps derived from the “Full Data + Meta Pipeline Audit Plan (SDD Edition)” in `docs/specs/plan.md`.

### 7.1 Phase 371: Path Determinism Sweep
**Goal**: Remove brittle, environment-dependent path literals from core tooling.

Requirements:
1. All scripts MUST derive filesystem paths from `TradingViewScraperSettings` when a settings field exists:
   - `settings.summaries_runs_dir` (never `artifacts/summaries/...`)
   - `settings.lakehouse_dir` (never `Path("data/lakehouse")` in core logic)
   - `settings.export_dir` (never `Path("export")`)
2. Legacy fallbacks are permitted only if:
   - they are settings-derived, and
   - they are explicitly logged (for auditability).

### 7.2 Phase 372: Alpha Read-Only Enforcement
**Goal**: Make it difficult/impossible to accidentally introduce network I/O into the Alpha cycle.

Requirements:
1. Any “alpha/prep” entrypoint MUST default to **read-only** mode (Lakehouse-only).
2. Network ingestion MUST be an explicit opt-in and MUST be treated as DataOps (not Alpha).
3. If a network path is requested but unsupported, the script MUST fail fast with a clear remediation message (e.g., “run `make flow-data` first”).

### 7.3 Phase 373: Modular Pipeline Safety
**Goal**: Ensure modular pipelines (`tradingview_scraper/pipelines/*`) are safe by default.

Requirements:
1. Modular pipeline stages MUST NOT silently read from shared mutable locations unless explicitly configured.
2. Defaults MUST bias toward **run-dir isolation**:
   - if a stage needs `candidates` / `returns`, it SHOULD first look in `settings.summaries_runs_dir / <run_id> / data/`.
3. Legacy fallbacks to shared mutable locations (e.g., `settings.lakehouse_dir`) are permitted only if:
   - `TV_STRICT_ISOLATION != 1`, and
   - the stage logs that it used a fallback path.
4. When `TV_STRICT_ISOLATION=1`, modular stages MUST fail fast if run-dir inputs are missing (no shared fallbacks).

### 7.4 Phase 374: Validation Tools “No Padding” Compliance
**Goal**: Prevent validation/reporting utilities from introducing calendar artifacts.

Requirements:
1. Validation tools MUST NOT `fillna(0.0)` to align returns for TradFi or mixed calendar computations.
2. Alignment MUST use calendar-safe joins:
   - inner join on dates for mixed calendars
   - explicit reporting of how many rows were dropped due to alignment
3. Validation tools MUST resolve run directories via settings, not hard-coded paths.

---

## 8. Phase 380: Contract Tightening (SDD + TDD)

This phase tightens **DataOps boundary contracts** to prevent “silent shape drift” from propagating
into selection, optimization, and meta ensembling.

### 8.1 Candidate Schema Contract (Canonical)

The platform defines a canonical candidate record schema (compatible with `CandidateMetadata`):

Required fields:
1. `symbol` MUST be a string in `EXCHANGE:SYMBOL` format.
2. `exchange` MUST be a string equal to the `symbol` prefix.
3. `asset_type` MUST be a non-empty string (default `"spot"` if unknown).
4. `identity` MUST be exactly `EXCHANGE:SYMBOL` (single prefix; equals `symbol`).
5. `metadata` MUST be a dict (free-form; can store scanner-specific fields).

Optional fields (when known):
- `market_cap_rank`, `volume_24h`, `sector`, `industry`

### 8.2 DataOps Validator Gate (Fail-Fast)

The DataOps consolidation boundary MUST normalize and validate all discovery exports before
writing `data/lakehouse/portfolio_candidates.json`.

Requirements:
1. Heterogeneous inputs MAY be normalized (e.g., legacy `"Symbol"` → `"symbol"`), but outputs MUST be canonical.
2. When strict schema is enabled (`TV_STRICT_CANDIDATE_SCHEMA=1` or `TV_STRICT_HEALTH=1`), invalid records MUST raise
   and fail the DataOps run (no silent drops).
3. When strict schema is disabled, invalid records MAY be dropped, but the count MUST be logged.

### 8.3 Deterministic Consolidation Semantics
 
 To preserve reproducibility:
 1. Candidate export files MUST be processed deterministically (stable ordering).
 2. Duplicate candidates MUST be de-duplicated by canonical `symbol`.
 3. Duplicate candidate metadata MUST be merged deterministically (do not lose fields).
 
 ## 9. Telemetry & Compute Resilience (v3.7+)
 
 ### 9.1 Observability Standard (OpenTelemetry)
 1. **Signal Unification**: The platform MUST utilize the standard OpenTelemetry APIs for all observability signals: Tracing, Metrics, and Logging.
 2. **Standard APIs**:
    - **Tracing**: Use `opentelemetry.trace.get_tracer` for span management.
    - **Metrics**: Use `opentelemetry.metrics.get_meter` for instrument management (Histograms, Counters, Gauges).
    - **Logging**: Use `opentelemetry.sdk.logs` and the standard Python `logging` bridge (OTel `LoggingHandler`).
 3. **Backend Neutrality**: The platform MUST NOT couple business logic to specific backends (e.g., Prometheus/Jaeger). Signal delivery MUST be configurable via standard OTel environment variables (e.g., `OTEL_EXPORTER_OTLP_ENDPOINT`).
 4. **Context Propagation**: The `trace_id` MUST be propagated across all distributed boundaries (Ray workers, child processes) using standard W3C TraceContext headers.
 5. **Unified Logging**: Logs MUST be structured and MUST include `trace_id` and `span_id` linked to the active OTel context.
 6. **Forensic Telemetry**: Every production run MUST persist its full OTel trace (spans and durations) to a `forensic_trace.json` file in the run directory for performance auditing.
 7. **Distributed Trace Unification**: Traces generated on parallel Ray worker nodes MUST be collected and unified into the master `forensic_trace.json` to provide a complete view of distributed executions.
 
 ### 9.2 Ray Lifecycle & Resource Management
 1. **Graceful Shutdown**: The `RayComputeEngine` MUST ensure `ray.shutdown()` is called upon task completion or failure to prevent resource leakage.
 2. **Resource Capping**: Parallel executions MUST respect environment-defined CPU and memory limits (`TV_ORCH_CPUS`, `TV_ORCH_MEM_GB`).
 3. **Process Isolation**: Each strategy sleeve execution MUST occur in a stateful Ray Actor with an isolated workspace and environment.
 
 ## 10. The Atomic Life Cycle Standard (v3.8+)
 
 The platform formalizes the "Atomic Life Cycle" for portfolio sleeves, ensuring a deterministic transition from raw data to executable weights.
 
 ### 10.1 Logic Stages (L0-L4)
 
 1. **Foundation (L0)**: The immutable state of the Lakehouse.
 2. **Ingestion Gate (L1)**: Pre-flight data contract validation and Point-in-Time (PIT) fidelity checks.
 3. **Selection & Inference (L2)**: Natural selection (HTR) and alpha scoring (Log-MPS).
 4. **Strategy Synthesis (L3)**: Composition of Strategy Atoms (Asset + Logic + Direction) and Synthetic Long normalization.
 5. **Risk Allocation & Deployment (L4)**: Convex optimization and Physical Weight flattening.
 
 ### 10.2 Mandatory Execution Sequence
 
 Every atomic production run MUST execute the following sequence:
 1. **Foundation Gate**: Validate Lakehouse existence and schema.
 2. **Recruitment**: Settle the raw candidate pool from discovery exports.
 3. **Natural Selection**: Apply HTR v3.4 loops.
 4. **Enrichment**: Link winners to structural metadata.
 5. **Synthesis**: Transform asset returns into synthetic alpha streams.
 6. **Regime Detection**: Detect volatility quadrant using HMM classifiers.
 7. **Optimization**: Allocate weights via bounded convex solvers.
 8. **Flattening**: Collapse alpha weights into asset-level weights.
 9. **Forensic Report**: Generate a unified tear-sheet linked by a single `trace_id`.
 
 ## 11. DataOps & MLOps Governance
 
 ### 11.1 Data Contract Standard
 1. **Schema Validation**: Every stage MUST define its input/output schema.
 2. **"No Padding" Compliance**: Returns matrices MUST NOT be zero-filled for TradFi calendars.
 3. **Toxicity Bounds**: Assets with $|r_d| > 500\%$ MUST be automatically dropped.
 
 ### 11.2 Model Lineage & Immutability
 1. **Snapshot Isolation**: When a run begins, the platform SHOULD create a symlink-based snapshot of the Lakehouse to ensure immutability.
 2. **Lineage Linkage**: Every optimized portfolio MUST link back to the exact version (timestamp/hash) of the `features_matrix.parquet` used for inference.
 3. **Traceability**: The `trace_id` MUST be injected into all audit ledger entries across all L0-L4 stages.
 4. **Forensic Telemetry**: Every production run MUST persist its full OTel trace (spans and durations) to a `forensic_trace.json` file in the run directory for performance auditing.
 5. **Distributed Trace Unification**: Traces generated on parallel Ray worker nodes MUST be collected and unified into the master `forensic_trace.json` to provide a complete view of distributed executions.
 
 ## 13. Advanced DataOps Hardening (v4.0+)
 
 ### 13.1 Microstructure Toxicity Standards
 1. **Price Stalls**: Assets with $> 3$ consecutive bars of zero price change (zero variance) MUST be vetoed if they are in a normally liquid asset class.
 2. **Volume Spikes**: Assets with a 1-day volume $> 10\sigma$ (10x standard deviation of trailing 20d volume) MUST be flagged as "Toxic Microstructure" and dropped.
 3. **Ghost Candles**: Crypto assets with zero volume during active trading windows MUST be flagged for repair or removal.
 
 ### 13.2 Automated Foundation Resilience
 1. **Repair-Mandatory Lifecycle**: The DataOps pipeline (`flow-data`) MUST include a mandatory repair pass. No foundation is considered "Golden" until all discoverable gaps are either filled or declared unrepairable.
 2. **Health Registry**: The Lakehouse MUST maintain a `foundation_health.json` registry tracking the audit hash and repair status of every symbol.
 3. **Fail-Fast Foundation Gate**: The Alpha pipeline MUST abort if any required symbol in the run manifest lacks a "Healthy" status in the foundation registry.

 ## 14. Multi-Engine Selection Policy (v4.1+)
 
 ### 14.1 Ensemble Scoring
 1. **Weight of Evidence (WoE)**: Selection decisions MUST be backed by multiple independent ranking engines (e.g., Log-MPS + Signal Quality + Regime Fit).
 2. **Dynamic Weighting**: Ranker weights MUST be adjustable via the pipeline manifest to allow tuning for specific market environments.
 3. **Consensus Requirement**: Candidates MUST meet a minimum ensemble score threshold to be recruited into the winning pool, ensuring high-conviction selection.

 ## 15. Real-time Pipeline Monitoring (v4.2+)
 
 ### 15.1 Metrics Exposure
 1. **Prometheus Standard**: The platform MUST expose execution metrics (durations, success/failure counts, resource usage) via a Prometheus-compatible scrape endpoint or Pushgateway.
 2. **Stage-Level Granularity**: Metrics MUST be emitted at the individual stage level, allowing for bottleneck identification in real-time.
 3. **Live Dashboards**: The platform SHOULD provide Grafana dashboard templates for visualizing pipeline health, execution throughput, and alpha quality drift.

 ## 16. Numerical Stability & Fractal Safety (v4.3+)

 ### 16.1 Stable Sum Gate
 1. **Weight Conservation**: The weight flattening stage MUST verify that the sum of projected physical weights matches the original meta-allocation (tolerance: $1 \times 10^{-4}$).
 2. **Conservation Failure**: If weight leakage is detected, the system MUST log a warning. In strict stability mode (`TV_STRICT_STABILITY=1`), the pipeline MUST abort.

 ### 16.2 Fractal Recursion Guard
 1. **Depth Limit**: Recursive pipeline stages (Aggregation, Flattening) MUST enforce a maximum fractal depth (default = 3) to prevent infinite loops.
 2. **Cycle Detection**: The orchestrator MUST track the profile call stack and abort if a circular dependency is detected in the manifest.

 ## 17. Fractal Backtesting Protocol (v4.4+)
 
 ### 17.1 Recursive Walk-Forward
 1. **Two-Tier Optimization**: Meta-portfolio backtests MUST simulate rebalancing at both the atomic sleeve level and the meta-allocation level.
 2. **Dynamic Meta-Rebalancing**: At each rebalance window, the meta-allocation between sleeves MUST be re-calculated using the realized returns of those sleeves up to that point.
 3. **Performance Consistency**: Equity curves generated for a meta-portfolio MUST be the result of a continuous walk-forward process that accounts for sleeve-level churn and meta-level reallocation.

 ## 18. Feature Store PIT Integrity (v4.5+)
 
 ### 18.1 Point-in-Time Fidelity
 1. **Zero-Gap Backfill**: The global `features_matrix.parquet` MUST provide 100% coverage for all symbols present in the returns matrix for the active training window.
 2. **NaN Isolation**: Feature engineering MUST utilize a bounded forward-fill (`limit=3`) to prevent lookahead bias from stale data while ensuring numerical stability for ranking engines.
 3. **Consistency Veto**: If an asset's feature history contains $> 10\%$ missing values after warm-up, it MUST be vetoed from the selection pool.
 
 ## 12. The Unified DAG Orchestrator (v3.9+)
 
 The platform transitions from imperative script-based execution to a declarative Directed Acyclic Graph (DAG) model managed by the SDK.
 
 ### 12.1 Execution Model
 1. **Declarative Definition**: Pipelines MUST be defined as a sequence of addressable stage IDs (e.g., `["foundation.ingest", "alpha.inference", ...]`).
 2. **Context Persistence**: The `QuantSDK` MUST manage the lifecycle of the execution context, ensuring it is passed between stages and persisted to the run directory upon completion.
 3. **Atomic Rollback**: If any stage in the DAG fails, the orchestrator MUST mark the run as `FAILED` in the audit ledger and skip subsequent dependent stages.
 
 ### 12.2 Integration Standards
 1. **SDK-First**: All high-level workflows (`flow-production`, `flow-meta`) MUST be thin wrappers around `QuantSDK.run_pipeline()`.
 2. **Telemetry Coverage**: The DAG runner MUST create a root span for the entire pipeline and child spans for each stage, preserving the parent `trace_id`.
 3. **Resource Provisioning**: For parallel branches in the DAG, the orchestrator MUST automatically provision Ray actors or tasks based on the stage category.

