# Natural Selection Specification (v1)
**Status**: Formalizing
**Date**: 2026-01-05

This document standardizes the “Natural Selection” stage of the pipeline:
raw discovery pool → selected candidate universe.

Primary implementation:
- `scripts/natural_selection.py`
- `tradingview_scraper/selection_engines/*`

This spec focuses on:
- artifact contracts (inputs/outputs),
- selection-mode semantics,
- audit requirements,
- and how multi-venue universes (TradFi/FX/crypto) are incorporated safely.

Related specs:
- `docs/specs/selection_intelligence_v1.md` (selection versioning and philosophy)
- `docs/specs/universe_atoms_and_perspectives_v1.md` (atoms/perspectives contract)
- `docs/specs/discovery_venue_coverage_matrix_v1.md` (venue expansion + calendar policy)
- `docs/specs/session_aware_auditing.md` (calendar integrity)

---

## 1) Inputs (Canonical)

Natural selection consumes:
1. **Returns matrix**:
   - `data/lakehouse/portfolio_returns.pkl`
2. **Raw candidate manifest**:
   - `data/lakehouse/portfolio_candidates_raw.json`
3. **Optional antifragility stats** (if present):
   - `data/lakehouse/antifragility_stats.json`

Preconditions:
- Candidate enrichment has been applied so execution metadata exists where required:
  - `tick_size`, `lot_size`, `price_precision` (minimum)
- Calendar integrity is preserved (no weekend padding for session-based assets).

---

## 2) Outputs (Selected Universe)

Natural selection produces:
1. **Selected candidates**:
   - `data/lakehouse/portfolio_candidates.json`
2. **Selection audit artifact** (run-scoped):
   - `artifacts/summaries/runs/<RUN_ID>/selection_audit.json`
   - (and a synchronized lakehouse copy at `data/lakehouse/selection_audit.json`)

The selected universe is the canonical input to:
- high-integrity data fetch (`make data-fetch LOOKBACK=...`)
- strict health audit (`make data-audit STRICT_HEALTH=1`)
- portfolio optimization (`make port-optimize`)
- tournament validation (`make port-test`)

---

## 3) Selection Modes (Versioned Engines)

Natural selection delegates the selection decision to a versioned selection engine:
- `mode` parameter (CLI) or `settings.features.selection_mode`

Examples:
- `v3.2` (Log-MPS; preferred default)
- `v2.1` (CARS; conservative anchor)

Engine responsibility:
- cluster the universe (or otherwise structure it),
- compute scores and vetoes,
- select winners per cluster,
- emit diagnostics + provenance.

Natural selection responsibility:
- wire data and configuration into the engine,
- write outputs atomically,
- record audits (selection_audit + audit ledger).

---

## 4) Parameters (Standard Knobs)

`scripts/natural_selection.py` supports:
- `top_n` (winners per cluster)
- `threshold` (distance / similarity threshold; interpretation depends on engine)
- `max_clusters`
- `min_momentum_score` (momentum gate)

Defaults are sourced from `TradingViewScraperSettings` and/or the active manifest profile.

Institutional standard (current intent):
- `v3.2` is optimized around breadth: `top_n = 5` as the default.

---

## 5) Audit Contract (Required)

### 5.1 selection_audit.json (run-scoped)
Must include (minimum):
- `total_raw_symbols`
- `total_selected`
- `lookbacks_used`
- cluster map (cluster sizes, winners)
- `spec_version` / engine version
- `vetoes` (rejected symbols + reasons)
- `metrics` (engine-level summary metrics)

### 5.2 audit.jsonl (ledger)
If `feat_audit_ledger` is enabled:
- record an intent/outcome pair for `natural_selection`
- include input hashes and output hashes
- include summary metrics (`raw_pool_count`, `selected_count`, `n_vetoes`, etc.)

Acceptance:
- selection can be replayed deterministically from the manifest snapshot + audited inputs.

---

## 6) Multi-Venue Universe Expansion (Policy)

We expand the raw pool breadth-first across venue classes (TradFi/FX/crypto), but we do not allow silent calendar mixing to degrade the returns matrix.

### 6.1 Canonical FX majors (G7/G8-oriented)
Near-term canonical FX atom set:
- USD-centric majors: `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`, `AUDUSD`
- Optional (after stability): `NZDUSD` and liquid crosses (`EURJPY`, `GBPJPY`, `EURGBP`)

Policy:
- FX atoms should be treated as a coherent 24/5 sleeve/perspective.
- Dedup must be stable (pair identity across venues).

Reference:
- `docs/specs/discovery_venue_coverage_matrix_v1.md`

### 6.2 Canonical crypto universe (majors + deterministic top-50)
Near-term canonical crypto atom set:
- Always include BTC, ETH (per viable exchange policy).
- Expand to a deterministic “top 50” set from viable CEX venues.

Policy:
- “Top-50” must be derived from observed liquidity in scanner exports (e.g., 30d median `Value.Traded`) and recorded in `audit.jsonl`.
- “Viable exchanges” must be an explicit allowlist encoded in scanner configs and recorded in the run artifacts.
- Any symbol that is stale at selection time must be excluded from the **selected** universe in production runs (do not promote stale symbols into `STRICT_HEALTH=1`).

Reference:
- `docs/specs/discovery_venue_coverage_matrix_v1.md`

### 6.3 Sleeve-first mixing
Production default:
- Prefer multi-sleeve composition (TradFi sleeve, FX sleeve, crypto sleeve) over mixing all assets into one covariance model.
- Mixing policies must be explicit and audited (calendar alignment and freshness rules).

### 6.4 Canonical commodity proxies (ETF-first; session-based sleeve)
Near-term canonical commodity atom set (ETFs; session-based):
- Broad commodities: `NYSEARCA:DBC` or `NYSEARCA:PDBC`
- Gold: `NYSEARCA:GLD`
- Silver: `NYSEARCA:SLV`
- Oil: `NYSEARCA:USO` or `NYSEARCA:BNO`
- Industrial metals: `NYSEARCA:DBB` or `NYSEARCA:CPER`
- Agriculture (optional): `NYSEARCA:DBA`

Policy:
- Treat commodity proxies as part of the session-based TradFi sleeve (not crypto).
- Prefer ETF proxies until futures roll policies and contract metadata are production-grade.
- Enforce strict health for selected universes under production promotion (`STRICT_HEALTH=1`).

---

## 7) Acceptance Criteria (Institutional)

A natural selection run is “healthy” when:
- selected candidate file is written atomically and is non-empty,
- metadata coverage guardrail passes for selected candidates,
- selection_audit.json exists in the run directory and is internally consistent,
- audit ledger (if enabled) verifies and contains natural_selection intent/outcome records,
- selected universe can pass strict health audit under production policy.
