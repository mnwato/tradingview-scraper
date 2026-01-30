# Scanner Expansion (Breadth-First): Asset Types & Perspectives (v1)

## Goal
Expand discovery scanners **breadth-first** across distinct asset types (ETF-style categorization) so the selection engine sees multiple independent “perspectives” (risk drivers) rather than many near-duplicates inside one narrow equity cluster.

This is intentionally **not** a performance chase; it is a **coverage / robustness** initiative:
- Broader opportunity set for selection.
- Cleaner risk-bucket formation (factor + regime detection).
- Better calibration of strict-scoreboard gates against heterogeneous return behaviors.

Related multi-perspective roadmap:
- `docs/specs/universe_atoms_and_perspectives_v1.md` (defines atoms: instruments, ETFs, strategies, smart-money portfolios)
- `docs/specs/production_pipeline_status_and_expansion_roadmap_20260105.md` (status + phased expansion plan)
- `docs/specs/discovery_venue_coverage_matrix_v1.md` (breadth-first coverage across venue classes: TradFi/FX/crypto/futures/CFDs)

## Design Principles
1. **Breadth-first before depth**
   - Add one representative “slice” per asset type before adding dozens of variants inside any one slice.
2. **Proxy-first (ETF baskets / canonical proxies)**
   - Use stable, liquid proxies as the first implementation layer.
   - Only later expand into constituents, single names, or thinly traded tickers.
3. **Tag everything**
   - Every scanner output should attach at least:
     - `asset_type` (equity|bond|commodity|fx|crypto|rates|volatility|real_estate|multi_asset)
     - `region` (us|ex_us|global|em|developed|crypto_native)
     - `theme` / `sector` / `subclass` (optional but preferred)
4. **Auditability and reproducibility**
   - Scanner expansions must remain manifest-driven and produce traceable artifacts in `audit.jsonl`.
5. **Calendar integrity**
   - Do not “pad” returns matrices with weekend zeros for TradFi assets.
   - Treat session calendars as first-class constraints (see `docs/specs/session_aware_auditing.md`).

## Breadth Dimensions (Minimum Coverage Set)

### 1) Equities
- **US broad**: large cap, small cap, equal-weight proxy.
- **Sectors**: at least 1–2 sector slices (e.g., tech, financials) as distinct behavior clusters.
- **International**: developed ex-US, emerging markets.
- **Style / factors**: value, momentum, quality, low-vol (proxies).

### 2) Bonds / Rates
- **UST duration ladder**: short vs intermediate vs long duration.
- **Inflation protection**: TIPS proxy.
- **Credit**: investment grade vs high yield.
- **Rates curve sensitivity**: if available, include a rates/curve proxy.

### 3) Commodities
- **Energy**: oil / broad energy proxy.
- **Metals**: gold (risk-off proxy), industrial metals (cyclical proxy).
- **Agriculture**: a broad ag proxy (optional but useful for diversification).

Canonical commodity proxy atoms (ETF-first; v1 starting set):
- **Broad commodities**: `NYSEARCA:DBC` or `NYSEARCA:PDBC` (broad basket proxy)
- **Gold**: `NYSEARCA:GLD` (risk-off / inflation hedge proxy)
- **Silver**: `NYSEARCA:SLV` (high beta precious metal proxy)
- **Oil**: `NYSEARCA:USO` (WTI proxy) or `NYSEARCA:BNO` (Brent proxy)
- **Industrial metals**: `NYSEARCA:DBB` (base metals basket) or `NYSEARCA:CPER` (copper proxy)
- **Agriculture** (optional): `NYSEARCA:DBA` (broad agriculture proxy)

Notes:
- Exact tickers can be swapped for equivalent proxies depending on TradingView coverage and data health.
- Futures-based commodity exposures are Phase 3 (research-first) until roll policies are production-grade.

### 4) FX
- **Majors (G7/G8-oriented)**:
  - Base currency set: `USD`, `EUR`, `JPY`, `GBP`, `CAD` (G7) plus commonly traded “major” extensions `CHF`, `AUD`.
  - Minimum atom set (USD-centric): `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`, `AUDUSD`.
  - Optional expansions once stable: `NZDUSD` and high-liquidity crosses (e.g., `EURJPY`, `GBPJPY`, `EURGBP`).
- **Risk proxies**: commodity FX (AUDUSD, USDCAD) and a risk-off proxy (USDCHF) where appropriate.

### 5) Crypto
- **Majors**: BTC, ETH (as distinct regimes).
- **Top-50 (viable exchanges)**: expand beyond majors to a “top 50” crypto atom set derived from viable venues (CEX) with explicit freshness/liquidity rules.
  - Selection intent: the “top 50” list must be deterministic and auditable (e.g., top by 30d median `Value.Traded` among supported venues), not a manual/ad-hoc market-cap scrape.
- **Market beta**: a total-market proxy if supported by the data source.
- **Avoid thin / stale alts by default**: only admit alts after freshness and survivorship checks are proven stable.

### 6) Real Estate / Inflation / “Macro”
- **REIT proxy**: real-estate behavior cluster distinct from equities.
- **Inflation / macro hedges**: if supported by your data sources (later phase).

### 7) Volatility / Defensive proxies (optional, data-source dependent)
- Volatility ETNs/indices or volatility-proxy instruments, if reliably supported by TradingView and the pipeline.

## Implementation Sketch (Phased)

### Phase A — Canonical Proxy Baskets (Low Risk)
1. Create curated “proxy baskets” per asset type (small lists).
2. Update scanners to emit these symbols + attach tags (`asset_type`, `region`, `subclass`).
3. Run small-scale production-parity smokes to ensure:
   - Health/audit passes for selected assets.
   - Strict-scoreboard candidates remain non-empty.

### Phase B — Expand Within Each Slice (Controlled Depth)
1. Add more sector/region variants only after the canonical set is stable.
2. Add liquidity/freshness rules that are explicit and audited.

### Phase C — Constituent Expansion (High Risk, Optional)
Expand into constituents (e.g., top holdings) only once:
- metadata enrichment is stable,
- session-aware audit is enforced,
- and strict gating remains non-empty without special-casing.

## Acceptance Criteria (Institutional)
- A production-parity mini-matrix smoke produces **non-empty non-baseline strict candidates**.
- Baseline reference rows (including `benchmark`) are present, audit-complete, and readable as anchors/calibration.
- Scanner additions do not introduce systematic `STALE` failures in selected universes without an explicit policy decision.
