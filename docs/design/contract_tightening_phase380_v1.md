# Design: Phase 380 — Contract Tightening (Candidate Schema Gate)

## 1. Context

The platform’s pipelines are intentionally decoupled:
- **Discovery** produces candidate lists.
- **DataOps** ingests/repairs lakehouse data and emits “golden copy” artifacts.
- **Alpha / Meta** consumes lakehouse + run-dir snapshots as read-only inputs.

This architecture is only safe if *boundary artifacts are contract-stable*.

Historically, candidate lists have existed in multiple shapes:
- legacy keys (`"Symbol"`, `"Exchange"`, `"type"`)
- structured keys (`"symbol"`, `"exchange"`, `"asset_type"`, `"identity"`, `"metadata"`)
- envelopes (`{"data": [...]}`)

Without a schema gate, this can cause “silent shape drift” where downstream stages receive
partial/mis-keyed candidate records and behave incorrectly.

## 2. Goals

1. Ensure all candidates entering the lakehouse are **canonical**.
2. Ensure DataOps can run in **strict mode** and fail fast on invalid candidate records.
3. Preserve **determinism** (stable ordering and stable merge semantics for duplicates).

## 3. Non-Goals

- Designing a new discovery architecture.
- Enforcing domain-specific metadata completeness (e.g. sector/industry required).
  Those are separate coverage/audit gates.

## 4. Canonical Candidate Schema

Canonical record (compatible with `CandidateMetadata` as dict):
- `symbol`: `EXCHANGE:SYMBOL` (string)
- `exchange`: `EXCHANGE` (string, equals prefix of `symbol`)
- `asset_type`: `"spot" | "perp" | "equity" | "etf" | ...`
- `identity`: exactly equals `symbol`
- `metadata`: dict (free-form)

Optional:
- `market_cap_rank`, `volume_24h`, `sector`, `industry`

## 5. Strictness Model

Strict schema mode is enabled when either condition is true:
- `TV_STRICT_CANDIDATE_SCHEMA=1`, or
- `TV_STRICT_HEALTH=1` (institutional “strict run” umbrella)

Behavior:
- **Strict**: invalid/unrecoverable records raise immediately (DataOps run fails).
- **Non-strict**: invalid records are dropped; drop count is logged.

## 6. Normalization Algorithm (Deterministic)

Normalization accepts heterogeneous dicts and produces canonical output:
1. Resolve `symbol` from `symbol` or legacy `Symbol`.
2. Resolve `exchange` from `exchange` or legacy `Exchange`.
3. If `symbol` is already prefixed (`EXCHANGE:SYMBOL`):
   - derive exchange from prefix if missing.
   - if exchange is present but mismatched:
     - strict: raise
     - non-strict: prefer prefix, preserve original under `metadata._exchange_original`.
4. If `symbol` is not prefixed:
   - strict: require exchange (else raise)
   - non-strict: exchange defaults to `"UNKNOWN"`
   - construct `symbol = f"{exchange}:{symbol}"`
5. `identity` is forced to exactly equal `symbol` (single-prefix invariant).
6. `metadata` is ensured to be a dict and absorbs any non-canonical keys so we do not lose information.

Deterministic consolidation:
- Export files are processed in stable (sorted) order.
- Duplicates are keyed by canonical `symbol`.
- Duplicate `metadata` is merged with stable semantics (first record wins; later records fill missing keys).

## 7. Implementation

Core helpers:
- `tradingview_scraper/utils/candidates.py`
  - `normalize_candidate_record(raw, strict=...) -> dict | None`

DataOps entrypoint:
- `scripts/services/consolidate_candidates.py`
  - applies normalization to each candidate record
  - dedupes by canonical `symbol`
  - merges metadata for duplicates
  - supports strict schema mode

## 8. Test Plan (TDD)

File: `tests/test_phase380_contract_tightening.py`

Cases:
1. Mixed legacy + structured inputs normalize into canonical schema and dedupe correctly.
2. Strict schema mode raises on invalid records (e.g. missing symbol).

