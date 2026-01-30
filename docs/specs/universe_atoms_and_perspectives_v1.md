# Universe “Atoms” & Multi-Perspective Portfolio Building (v1)
**Status**: Production Standard
**Date**: 2026-01-13 (Standardized in Phase 130)

## 10. End-to-End Selection Pipeline Standard (v2.0)
To ensure institutional reproducibility, the platform implements a standardized six-stage selection funnel.

### 10.1 Stage 1: Multi-Sleeve Discovery
- **Input**: L4 Scanners (Momentum, Trend, MeanReversion).
- **Process**: Unified data ingestion into the Lakehouse.

### 10.2 Stage 2: Canonical Consolidation
- **Process**: Deduplication by economic identity.
- **Rule**: Selection of the most liquid venue (Value.Traded) for the "Raw Pool."
- **Artifact**: `portfolio_candidates.json` (The Raw Pool).

### 10.3 Stage 3: Metadata-Aware Filtering (Pillar 1)
- **Process**: Multiplicative Probability Scoring (Log-MPS).
- **Factors**: Momentum, Stability, Liquidity, Antifragility, Survival, Efficiency, Entropy, Hurst, and Trend-Conviction (ADX).

### 10.4 Stage 4: Factor-Based Partitioning (Clustering)
- **Process**: Hierarchical Clustering (Ward Linkage) on raw return correlations.
- **Standard**: Identifies logical alpha clusters in price-space.

### 10.5 Stage 5: Conviction-Weighted Recruitment
- **Rule**: Select Top-N (default: 3) highest Log-MPS performers *within* each cluster.
- **Purity**: Ensures the highest conviction representatives for every identified factor.

### 10.6 Stage 6: Recursive Strategy Synthesis (Pillar 2)
- **Process**: Generation of Strategy Atoms `(Asset, Logic, Direction)`.
- **Normalization**: SHORT inversion with a -100% loss cap to prepare for Pillar 3:
  - $R_{syn,long} = R_{raw}$
  - $R_{syn,short} = -clip(R_{raw}, upper=1.0)$
- **Implementation**: Handled by `SynthesisStage` in the v4 MLOps pipeline.

## 11. Traceability & Audit Standards
- **Non-Negotiable**: Every stage MUST emit decision records to `audit.jsonl`.
- **Traceability**: A single ticker must be traceable from the initial L4 signal to its final portfolio weight.
- **v4 Compliance**: The `SelectionContext` audit trail satisfies this requirement by logging every stage transition.

## 0. Intent
We want the platform to build portfolios not only from **low-correlated assets**, but also from:
- **Strategies** (return streams from engines/profiles),
- **ETFs** (proxy baskets for asset types and macro sleeves),
- **Smart-money portfolios** (publicly observable portfolio constructions, treated as “atoms”),
- and any other perspective that can be represented as a **return stream** and clustered/correlated.

This document defines a shared vocabulary and data contracts to support a **multi-perspective universe** while keeping institutional reproducibility and auditability intact.

---

## 1. Definitions

### 1.1 Atom
An **Atom** is the smallest unit we can allocate capital to *in a given layer*.

Atoms are not restricted to “a single ticker”.

Examples:
- **Instrument atom**: `NASDAQ:AAPL`, `BINANCE:BTCUSDT`, `TVC:DXY`
- **ETF atom**: `NYSEARCA:TLT`, `NYSEARCA:GLD`, `NYSEARCA:SPY`
- **Strategy atom**: `strategy:v3.2|rebalance=window|engine=skfolio|profile=hrp|sim=cvxportfolio`
- **Smart-money atom**: `portfolio:13f|manager=...|variant=top20_equal_weight`

### 1.2 Perspective (Universe View)
A **Perspective** is a coherent family of atoms with consistent:
- provenance (how they are discovered),
- audit/health policy (freshness and gaps),
- available metadata,
- and implementation semantics.

We treat each perspective as a **universe view** that can be selected, clustered, and allocated independently, then combined into a meta-portfolio.

---

## 2. Required Data Contracts

### 2.1 Atom Registry (canonical)
Create and maintain a run-scoped “atom registry” artifact.

**Proposed schema** (table/parquet preferred):
- `atom_id` (string; stable unique key)
- `atom_type` (enum: `instrument|etf|strategy|portfolio`)
- `provider` (string; e.g. `tradingview|tournament|13f|manual`)
- `symbols` (list[string]; underlying instruments, if applicable)
- `weights` (optional list[float]; underlying weights, if applicable)
- `asset_type` (string; e.g. `equity|bond|commodity|fx|crypto|real_estate|multi_asset`)
- `region` (string; `us|ex_us|global|em|developed|crypto_native`)
- `subclass` / `theme` / `sector` (optional strings)
- `calendar_type` (string; `tradfi|crypto|mixed`)
- `freshness_policy` (string; references health policy)
- `notes` (optional)

**Why**:
- makes discovery outputs comparable across perspectives,
- allows deterministic filtering (“only ETF atoms”, “only strategy atoms”),
- provides a single place to attach tags used by later correlation/clustering audits.

### 2.2 Atom Returns Matrix
Every perspective that participates in clustering/allocation must produce:
- a returns matrix `R[t, atom_id]`,
- aligned on a clearly specified calendar policy (see `docs/specs/session_aware_auditing.md`),
- and audited for gaps (policy differs by perspective).

**Non-negotiable**:
- Never zero-fill weekends for TradFi.
- Always record the effective calendar alignment method in `audit.jsonl`.

### 2.3 Audit Ledger Expectations
Any “atom generation” step must emit an `audit.jsonl` record with:
- input hashes (source artifacts),
- output hashes (atom registry + returns matrix),
- summary metrics (counts, gap stats, freshness stats).

---

## 3. Metrics: Finding “Uncorrelated Atoms”

### 3.1 Correlation → Distance
Base distance for clustering:
- `d(i,j) = sqrt(0.5 * (1 - corr(i,j)))`

Optional robustness extensions (research-only initially):
- tail correlation (crisis windows),
- regime-conditional correlation,
- mutual information / distance correlation (if/when implemented).

### 3.2 Clustering
Default (stable, interpretable):
- Hierarchical clustering + Ward linkage on correlation distance.

Acceptance criteria:
- cluster sizes are stable across nearby windows,
- cluster drift is measurable and logged (existing `monitor_cluster_drift.py` can be extended to atom types).

### 3.3 “Uncorrelated atoms” as a selection target
Do not treat “low correlation” as the only objective.

Instead:
- use clustering to avoid redundancy,
- then apply **within-cluster selection** (selection engines) to pick leaders,
- then allocate across clusters (HRP/barbell/min-variance depending on profile).

---

## 4. Perspectives (v1 Scope)

### 4.1 Instrument Universe (existing)
- Source: TradingView scanners (`make scan-run`), raw pool build, `make port-select`.
- Selection engines: v3.2 default (`top_n=5`).
- Allocation engines: `optimize_clustered_v2.py` (cluster-aware).
- Validation: tournament + strict scoreboard.

Coverage expansion intent (v1):
- **Crypto**: include BTC/ETH plus a deterministic “top 50” crypto set from viable exchanges (CEX) with strict freshness rules.
- **FX**: include G7/G8-oriented major FX pairs as a canonical baseline universe for 24/5 sleeve construction.
- **Commodities (proxy-first)**: include a small, canonical commodity proxy set (ETFs) as a TradFi sleeve (broad commodities, gold/silver, oil, industrial metals; agriculture optional).
  - Reference: `docs/specs/discovery_venue_coverage_matrix_v1.md`.

### 4.2 ETF Proxy Universe (next easiest)
Goal:
- fast coverage expansion across asset types (equity/bonds/commodities/FX/REITs).

Why ETFs:
- stable tickers, strong metadata,
- proxies for macro sleeves,
- easier to audit and reason about.

Implementation direction:
- curated proxy baskets per asset type (small lists),
- treat ETFs as first-class atoms (`atom_type=etf`) but still implementable instruments.

### 4.3 Strategy Universe (research-first)
Atoms:
- strategy return streams extracted from tournaments (engine/profile/simulator combinations).

Use:
- cluster strategies to identify orthogonal behaviors,
- allocate across strategies for “meta-portfolio” research.

Boundary (v1):
- This is a research layer unless we define a production mapping from strategy atoms → tradeable orders.

### 4.4 Smart-Money Portfolio Universe (future, optional)
Atoms:
- public portfolio constructions (e.g., 13F-based, ETF holdings-based “smart baskets”, etc.).

Risks:
- data sourcing and licensing,
- reporting lags,
- survivorship biases.

Policy:
- keep as research-only until ingestion + audit are reliable and deterministic.

---

## 5. Proposed Pipeline Integration (Phased)

### Phase 0 — Status + Guardrails (Now)
- Lock strict-scoreboard semantics (baseline reference rows; fixed gates).
- Ensure production pipeline’s health/audit behavior is stable for selected universes.

### Phase 1 — ETF Proxy Sleeve (Production)
- Add a “proxy ETF universe” discovery path.
- Run the same selection + allocation stack on this sleeve.
- Validate strict-scoreboard candidates remain non-empty.

### Phase 2 — Multi-Sleeve Meta-Portfolio (Production)
- Combine sleeves:
  - `instrument` sleeve (selected winners),
  - `etf` sleeve (macro diversification),
  - (optional) `cash` / defensive anchors.
- Allocate across sleeves using HRP at the sleeve level.

### Phase 3 — Strategy Universe (Research)
- Derive strategy atoms from tournament return pickles.
- Cluster strategies and compute diversification metrics.
- Evaluate whether strategy diversity predicts robustness (strict-scoreboard survival).

### Phase 4 — Smart Money (Research)
- Implement deterministic ingestion → atom registry → returns matrix.
- Add audit + gap/freshness policy.

---

## 6. Deliverables (v1)
- A documented, auditable “Atom Registry” contract.
- A plan to implement ETF proxy baskets as a first expansion layer.
- A research pathway to treat strategies and portfolios as atoms without weakening strict production gates.
