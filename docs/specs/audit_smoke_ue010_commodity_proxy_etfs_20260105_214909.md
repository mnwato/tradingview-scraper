# Audit Note: UE-010 Commodity Proxy ETF Basket Smoke — Run `20260105-214909`

This note audits UE-010 as an end-to-end discovery → data → selection → tournament → strict scoreboard smoke using a **commodity proxy ETF basket** as the universe.

## 1) Goal
1. Validate that UE-010 can emit a deterministic commodity proxy ETF basket as a discovery/scanner path.
2. Run a production-parity mini-matrix tournament under the production default windowing (`180/40/20`).
3. Capture strict-scoreboard behavior (gating signals) for a commodity sleeve universe.

## 2) Run Identity
- Run ID: `20260105-214909`
- Windowing (from `audit.jsonl`): `train/test/step = 180/40/20`
- Tournament matrix:
  - selection: `v3.2`
  - rebalance: `window`
  - engines: `custom, skfolio`
  - profiles: `market, benchmark, hrp, barbell`
  - simulators: `custom, cvxportfolio, nautilus`

## 3) UE-010 Discovery: Commodity Proxy ETF Basket

### 3.1 Scanner config
- Scanner: `configs/scanners/tradfi/commodity_proxy_etfs.yaml`
- Base universe: `configs/base/universes/commodity_proxy_etfs.yaml`

### 3.2 Static universe support (why it exists)
During execution, TradingView screener-based scanners returned `0` rows (including existing scanners like `bond_trend`), making “screener-driven” discovery non-functional for this environment.

UE-010 therefore uses **static universe mode** (new selector behavior):
- `tradingview_scraper/futures_universe_selector.py` now supports `static_mode` + `static_symbols` in configs, emitting a deterministic basket even when the screener endpoint is unavailable.

### 3.3 Basket emitted (validated symbols)
Export artifact:
- `export/20260105-214909/universe_foundation_commodity_proxy_etfs_20260105-214920.json`

Basket symbols (v1):
- `AMEX:DBC` (broad commodities)
- `AMEX:GLD` (gold)
- `AMEX:SLV` (silver)
- `AMEX:USO` (oil proxy)
- `AMEX:DBB` (industrial/base metals)
- `AMEX:CPER` (copper proxy)
- `AMEX:DBA` (agriculture proxy)

Note:
- `PDBC` was removed after validation because it failed TradingView history resolution in this environment.

## 4) Data + Selection

### 4.1 Canonical raw pool
- Raw candidates: `data/lakehouse/portfolio_candidates_raw.json` (7 symbols)
- Canonical returns (after benchmark injection): `data/lakehouse/portfolio_returns_raw.pkl` includes 8 symbols:
  - commodities basket + `AMEX:SPY` (benchmark baseline injection)

### 4.2 Selected universe (natural selection)
Selection outcome:
- `data/lakehouse/portfolio_candidates.json` contains 4 symbols:
  - `AMEX:GLD`, `AMEX:SLV`, `AMEX:DBB`, `AMEX:SPY`

Observed selection vetoes (from `port-select`):
- ECI vs negative alpha vetoes removed some commodity exposures (notably `DBC`, `USO`, `DBA`).

### 4.3 Strict health audit
`make data-audit STRICT_HEALTH=1` passed for:
- RAW universe (8/8 OK)
- SELECTED universe (4/4 OK)

## 5) Strict Scoreboard Outcome

Scoreboard outputs:
- `artifacts/summaries/runs/20260105-214909/data/tournament_scoreboard.csv`
- `artifacts/summaries/runs/20260105-214909/data/tournament_candidates.csv`
- `artifacts/summaries/runs/20260105-214909/reports/research/tournament_scoreboard.md`

Summary:
- Scoreboard rows: 33
- Strict candidates: 0 (empty `tournament_candidates.csv`)

Dominant vetoes:
- `cvar_mult` (24/33) and `sim_parity` (24/33) dominate.
- Secondary: `mdd_mult` (9/33), `af_dist` (9/33)

Interpretation:
- Commodity sleeve portfolios tend to have materially different tail behavior vs the baseline `market` reference (SPY), making `cvar_mult` a strong exclusion criterion.
- Nautilus parity remains a strong veto in this universe, suggesting simulator assumptions diverge materially for commodity exposures (worth tracking under the parity gate issue backlog).

## 6) Audit Ledger Integrity
- Audit ledger: `artifacts/summaries/runs/20260105-214909/audit.jsonl`
- Hash chain verified:
  - `uv run scripts/archive/verify_ledger.py artifacts/summaries/runs/20260105-214909/audit.jsonl` ✅

## 7) Next Actions (UE-010)
1. **Document symbol namespace reality**: many US ETFs resolve under `AMEX:` or `NASDAQ:` depending on the ticker. Prefer using `scanner.tradingview.com/symbol?symbol=...` validation when curating baskets.
2. **Commodity sleeve gate calibration** (policy question):
   - decide whether `cvar_mult` relative to `market` should be a hard strict gate for commodity sleeves, or treated as a calibration signal for sleeve-level allocation.
3. **Parity deep dive**:
   - measure `parity_ann_return_gap` distributions for commodity sleeves and identify whether the nautilus proxy assumptions are the root cause.

