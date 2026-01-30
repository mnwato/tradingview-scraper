# Discovery Venue Coverage Matrix (v1)
**Status**: Proposal
**Date**: 2026-01-05

This spec defines a breadth-first plan to expand discovery across **venue classes** (exchange types) while preserving:
- deterministic scanner configs,
- calendar integrity,
- and production-grade health/freshness gates.

It complements:
- `docs/specs/scanner_expansion_breadth_first_asset_types_v1.md` (asset-type breadth)
- `docs/specs/universe_atoms_and_perspectives_v1.md` (atoms/perspectives contract)
- `docs/specs/live_trading_promotion_pipeline_v1.md` (promotion to execution)

---

## 1) Venue Classes (Coverage Targets)

### A) TradFi Equities / ETFs
- **Examples**: NYSE, NASDAQ, AMEX (TradingView qualified tickers).
- **Calendar**: session-based (no weekend padding).
- **Freshness**: market-day based.
- **Initial breadth objective**: broad equity indices + ETF proxies for macro sleeves.

### B) Bonds / Rates (via ETFs first)
- **Why**: direct bond feeds are operationally complex; ETFs provide stable proxies.
- **Calendar**: session-based.

### C) Commodities (via ETFs first; futures later)
- **Why**: futures need roll policy and contract metadata to be production-safe.
- **Calendar**: session-based for ETFs; contract-specific for futures.
- **Canonical commodity proxy atoms (ETF-first; v1 starting set)**:
  - Broad commodities: `NYSEARCA:DBC` or `NYSEARCA:PDBC`
  - Gold: `NYSEARCA:GLD`
  - Silver: `NYSEARCA:SLV`
  - Oil: `NYSEARCA:USO` (WTI) or `NYSEARCA:BNO` (Brent)
  - Industrial metals: `NYSEARCA:DBB` or `NYSEARCA:CPER`
  - Agriculture (optional): `NYSEARCA:DBA`
  - Policy: treat these as session-based instruments and enforce the same strict health gates as other TradFi sleeves.

### D) FX (Spot)
- **Calendar**: near-24/5 with session-aware normalization.
- **Notes**: dedup rules (pair identity) must remain stable across venues.
- **Canonical major atoms (G7/G8-oriented)**:
  - Currency set: `USD`, `EUR`, `JPY`, `GBP`, `CAD` (G7), plus commonly traded majors `CHF`, `AUD`.
  - Minimum pairs (USD-centric): `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`, `AUDUSD`.
  - Optional (after stability): `NZDUSD` and liquid crosses (e.g., `EURJPY`, `GBPJPY`, `EURGBP`).

### E) Futures (Contracts)
- **Calendar**: contract-specific sessions; roll policies required for production.
- **Phase policy**: research-first until roll + continuous contract policy is locked.

### F) Crypto CEX (24/7)
- **Calendar**: 24/7; freshness is hour-based.
- **Operational risk**: stale venue symbols are common; selection must enforce freshness to avoid strict-health failures in production.
- **Canonical crypto atoms**:
  - **Majors**: BTC, ETH are always included (per venue policy).
  - **Top-50 (viable exchanges)**: expand to a “top 50” crypto universe sourced from viable exchanges only.
    - “Top-50” must be deterministic and auditable (preferred: top by 30d median `Value.Traded` within the scan export universe), not a manual market-cap scrape.
    - “Viable exchanges” is an explicit allowlist (e.g., `BINANCE`, `COINBASE`, `KRAKEN`, `OKX`, etc.) maintained in scanner configs/presets and recorded in `audit.jsonl`.
    - Production policy: if a symbol is stale at selection time, it is excluded from the selected universe (no silent promotion of stale symbols into `STRICT_HEALTH=1`).

### G) CFDs (Broker-defined)
- **Calendar**: broker-defined, higher operational ambiguity.
- **Phase policy**: research-only until calendar/freshness policies are proven stable.

---

## 2) Required Tagging (Discovery Outputs)

Every discovered symbol/candidate should carry tags sufficient to drive:
- filtering,
- clustering coverage reports,
- and “mixing policy” enforcement.

Minimum tags:
- `venue_class`: `equity|etf|fx|futures|crypto|cfd`
- `exchange`: `NASDAQ|NYSE|BINANCE|...` (as available)
- `asset_type`: `equity|bond|commodity|fx|crypto|real_estate|multi_asset`
- `calendar_type`: `tradfi|crypto|mixed`
- `region`: `us|ex_us|global|em|developed|crypto_native`

Enforcement:
- Missing tags are acceptable in early discovery exports, but must be filled by enrichment before selection/optimization.

---

## 3) Mixing Policy (Calendars + Health)

Default policy (production):
- Do not mix calendar types inside the same returns matrix without explicit normalization rules.
- Prefer “multi-sleeve” composition over mixing:
  - sleeve A: session-based (TradFi/ETFs),
  - sleeve B: 24/7 (crypto),
  - sleeve C: FX (24/5).

Health policy (production):
- Selected universe must pass strict health (`make data-audit STRICT_HEALTH=1`).
- Any exceptions (e.g., crypto freshness tolerance) must be explicit and documented.

---

## 4) Breadth-First Execution Plan (Practical)

Phase 1 (lowest risk):
1. Expand TradFi ETFs (proxy baskets) across asset types.
2. Expand FX majors (G7/G8-oriented) with stable dedup policy.
3. Crypto majors + a deterministic “top 50” derived from viable exchanges (with explicit freshness/liquidity rules).

Phase 2 (controlled complexity):
1. Add commodity proxies (ETFs first).
2. Add additional equity regions (ex-US, EM).

Phase 3 (research-first):
1. Futures (roll policy + contract metadata).
2. CFDs (broker calendars).
3. Smart-money portfolio ingestion (lagged data).

Acceptance at each phase:
- selection produces a non-empty candidate universe,
- portfolio optimization runs end-to-end,
- strict-scoreboard produces non-empty **non-baseline** candidates for production-parity smokes,
- strict health passes for selected universe (production candidates only).

---

## 5) References (Existing Presets)
- Crypto presets: `docs/specs/crypto_cex_presets.rst`
- Forex presets: `docs/specs/forex_presets.rst`
- Futures selector: `docs/specs/futures_universe_selector.rst`
- CFD presets: `docs/specs/cfd_presets.rst`
