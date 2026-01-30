# Execution Plan: Multi-Perspective Universe Expansion (2026 Q1)
**Status**: Proposed
**Date**: 2026-01-05

This plan converts the “multi-perspective atoms” roadmap into concrete, auditable tasks that can be executed without weakening strict production gates.

Primary specs:
- `docs/specs/universe_atoms_and_perspectives_v1.md`
- `docs/specs/scanner_expansion_breadth_first_asset_types_v1.md`
- `docs/specs/production_pipeline_status_and_expansion_roadmap_20260105.md`

## Guiding Constraints
1. **Strict gates remain strict**: production eligibility continues to be determined by the strict-scoreboard thresholds (and explicit health audits).
2. **Research-only signals stay non-gating** until promoted by an explicit spec update.
3. **Calendar integrity**: no weekend padding for TradFi; session-aware alignment is enforced.
4. **Audit-first**: every new producer emits hashes and summary metrics into `audit.jsonl`.

---

## UE-000 — Baseline: Production Pipeline Status Check (repeatable)
**Goal**: make “ready for production” a falsifiable claim.

Actions:
- Verify the full pipeline produces run-scoped artifacts: discovery → raw → selected → optimize → tournament → scoreboard.
- Identify any stage that breaks under strict health for the selected universe.

Acceptance:
- `make flow-production PROFILE=production` completes OR fails for a single named, actionable reason (no silent drift).
- `audit.jsonl` hash chain verifies.

---

## UE-010 — ETF Proxy Universe (Production Sleeve, Small Canonical Set)
**Goal**: introduce breadth via implementable, auditable proxies.

Actions:
- Define a curated ETF proxy “basket” per asset type (equity, bonds, commodities, FX proxy, REIT).
- Add discovery/scanner path that emits this basket deterministically.
- Tag these candidates (`asset_type`, `region`, `subclass`) and ensure metadata enrichment covers execution fields.

Canonical commodities (v1, ETF-first):
- Broad commodities: `NYSEARCA:DBC` or `NYSEARCA:PDBC`
- Gold: `NYSEARCA:GLD`
- Oil: `NYSEARCA:USO` or `NYSEARCA:BNO`
- Industrial metals: `NYSEARCA:DBB` or `NYSEARCA:CPER`
- Optional diversifier: `NYSEARCA:DBA` (agriculture)

Acceptance:
- A production-parity mini-matrix smoke yields **non-empty non-baseline** strict candidates.
- ETF sleeve passes `make data-audit STRICT_HEALTH=1` for the selected universe.

Notes:
- ETFs are still instruments; they should use the existing selection/portfolio machinery with minimal special casing.

---

## UE-020 — Breadth-First Scanner Expansion by Asset Type (Production)
**Goal**: add one “slice” per asset type before depth within slices.

Actions:
- Extend discovery pipelines to include at least one slice each:
  - equities (US + ex-US),
  - bonds/rates,
  - commodities,
  - FX majors (G7/G8-oriented baseline set),
  - crypto majors + deterministic “top 50” from viable exchanges,
  - REIT proxy.
- Require tags so downstream clustering can report diversification coverage by `asset_type`.

Acceptance:
- Selected universe has measurable coverage across multiple `asset_type` groups.
- Cluster report shows fewer “mega clusters” dominated by one type when compared to equity-only discovery.

---

## UE-030 — Atom Registry Artifact (Plumbing)
**Goal**: make multi-perspective universes inspectable and comparable.

Actions:
- Implement a run-scoped “atom registry” artifact (table) with stable `atom_id` and tags.
- Ensure this artifact is referenced/hashes are recorded in the ledger.

Acceptance:
- For a run, operators can answer deterministically:
  - how many atoms exist per type,
  - which pipelines produced them,
  - and how those atoms map to returns columns.

---

## UE-040 — Strategy Universe (Research Layer, Derived from Tournament Runs)
**Goal**: treat strategy return streams as clusterable atoms.

Actions:
- Extract strategy return series from tournament artifacts (returns pickles).
- Build a strategy returns matrix `R[t, strategy_atom]`.
- Cluster strategy atoms and report “uncorrelated behaviors” as candidates for meta-allocation research.

Acceptance (research):
- Strategy clustering produces stable, interpretable groupings across nearby windows.
- A meta-portfolio of strategy atoms is evaluated via the same walk-forward framework (research-only).

Boundary:
- Production mapping from strategy atoms → orders is out of scope until explicitly specified.

---

## UE-050 — Smart-Money Portfolio Universe (Research Layer, Ingestion-Dependent)
**Goal**: treat public portfolios as atoms, without compromising reproducibility.

Actions:
- Define deterministic ingestion format (CSV/JSON) and archiving policy.
- Build portfolio returns series from holdings + price data.
- Apply health/freshness policy appropriate for lagged reporting.

Acceptance (research):
- Atom registry + returns matrix are reproducible with ledger hashes.
- Bias notes are documented (lags, survivorship, rebalance assumptions).

---

## UE-060 — Multi-Sleeve Meta-Portfolio (Production Candidate, After Gates Stabilize)
**Goal**: allocate across sleeves (instrument + ETF proxies; optionally others later).

Actions:
- Build within-sleeve portfolios (existing optimizers).
- Build across-sleeve allocation (HRP at sleeve level).

Acceptance:
- Strict-scoreboard candidates remain non-empty under production-parity smokes.
- Portfolio remains implementable and passes health + metadata gates.
