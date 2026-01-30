# Specification: Quantitative Workflow Pipeline
**Status**: Formalized
**Date**: 2025-12-31

## 1. Overview
This document defines the standardized pipeline for transforming raw market data into an optimized, multi-asset portfolio. The workflow is unified under a 15-step production sequence.

## 2. The 17-Step Production Sequence

The entire production lifecycle is managed via the **Python Orchestrator** (`scripts/run_production_pipeline.py`) and follows this rigorous sequence:

1.  **Cleanup**: Wipe incremental artifacts (`make clean-run`).
2.  **Environment Check**: Validate manifest and configuration integrity (`make env-check`).
3.  **Discovery**: Execute composable discovery scanners (`make scan-run`).
4.  **Aggregation**: Consolidate scans into a Raw Pool (`make data-prep-raw`).
5.  **Lightweight Prep**: Fetch 60-day history for analysis (`make data-fetch LOOKBACK=60`).
    - **Note**: Now produces `returns_matrix.parquet` with **Physical Symbols** (e.g. `BINANCE:BTCUSDT`).
6.  **Natural Selection**: Hierarchical clustering & XS Ranking (`make port-select`).
7.  **Enrichment**: Propagate metadata and descriptions (`make meta-refresh`).
8.  **High-Integrity Prep**: Fetch 500-day secular history for winners (`make data-fetch LOOKBACK=500`).
9.  **Strategy Synthesis** (New): Expand Physical Assets into Logic Atoms (Logic + Direction) (`uv run scripts/synthesize_strategy_matrix.py`).
    - Outputs `synthetic_returns.parquet`.
10. **Health Audit**: Validate 100% gap-free alignment (`make data-audit`).
11. **Persistence Analysis**: Analyze trend/mean-reversion persistence (`make research-persistence`).
12. **Regime Analysis**: Detect market regimes (Normal/Turbulent/Crisis) (`scripts/research_regime_v3.py`).
13. **Factor Analysis**: Build hierarchical risk buckets (`make port-analyze`).
14. **Optimization**: Cluster-Aware allocation with Turnover Control (`make port-optimize`).
    - Prioritizes `synthetic_returns.parquet` for Logic-Aware optimization.
15. **Validation**: Walk-Forward Tournament benchmarking (`make port-test`).
16. **Reporting**: QuantStats Tear-sheets & Alpha Audit (`make port-report`).
17. **Gist Sync**: Synchronize essential artifacts to private Gist (`make report-sync`).

## 3. Standard Production Configuration (v3.9.7)
Institutional stability requires robust lookback windows to prevent overfitting.

| Parameter | Value | Purpose |
| :--- | :--- | :--- |
| **Lookback Days** | `500` | Full secular cycle capture (Bull + Bear). |
| **Train Window** | `252` | 1-Year covariance estimation for stable risk parity. |
| **Test Window** | `20` | Monthly rebalance cadence. |
| **Step Size** | `20` | Monthly walk-forward step. |
| **Min Liquidity** | `$5M` | Binance Spot Floor (Wider funnel). |

## 4. Automation Commands
```bash
# Full institutional production lifecycle
make flow-production

# Rapid iteration development execution
make flow-dev

# Individual Namespace Commands:
make env-sync       # Sync dependencies
make scan-run       # Run discovery scanners
make data-fetch     # Ingest market data
make data-refresh-targeted # Force refresh for stale symbols
make data-repair    # High-intensity gap repair
make port-select    # Prune and select candidates
make port-optimize  # Convex risk allocation
make port-test      # Run benchmarking tournament
```

### Tournament Window Sizing (Minimum Data Requirement)
The tournament operates on the post-dropna returns matrix. Require:
`len(returns.dropna()) >= train_window + test_window`.
If the requirement is not met, the tournament returns early with "data too short".

**Stale symbol recovery (targeted):**
```bash
# Refresh a small stale subset, then rebuild the full universe
make data-refresh-targeted TARGETED_CANDIDATES=data/lakehouse/portfolio_candidates_targeted.json
make flow-dev
```

### Forex Base Universe Audit (Debugging)
```bash
# Fast: liquidity report only
make forex-analyze-fast

# Full: backfill + gap-fill + data health + clusters
BACKFILL=1 GAPFILL=1 FOREX_LOOKBACK_DAYS=365 make forex-analyze
```
- Produces run-scoped artifacts under `artifacts/summaries/runs/<RUN_ID>/` (report, data health CSV, cluster map + JSON).
- Default filter excludes IG-only singleton pairs (use `--include-excluded` to render them in the report).
- Clusters tend to separate into quote-currency blocks (e.g. JPY, CHF) plus cross themes (e.g. EUR/GBP vs AUD/NZD).

## 4. Universe Selectors (Scanners) — Current State

- **Core engine**: `FuturesUniverseSelector` is the generic selector used across Crypto, Equities, Forex, Futures, and CFDs.
- **Wrappers**: `BondUniverseSelector` and `cfd_universe_selector` are thin entrypoints that reuse the same selector plumbing.
- **Export contract**: scan artifacts are written to `export/<run_id>/universe_selector_*.json` using a `{meta,data}` envelope; consumers should prefer `meta` (with filename parsing as a fallback).
- **Forex dedup**: forex selectors dedupe by canonical pair identity (base+quote) across venues; aggregated `volume`/`Value.Traded` are preserved alongside representative `volume_rep`/`Value.Traded_rep` for execution-aware ranking.
- **Operational risks**:
  - configs are linted via `make scan-audit` (CI-safe), but TradingView fields can still change over time
  - scan orchestration is now manifest-driven via `make scan-run` (`scripts/compose_pipeline.py`), reducing drift from ad-hoc bash lists

## 5. Universe Selector Roadmap (Non-Breaking)

1. **Inventory & dependency map**: document producer→consumer coupling for `export/<run_id>/universe_selector_*.json` (which scripts still parse filenames vs read embedded `meta`).
2. **Config lint + deterministic tests**: validate all layered configs (`configs/base/`, `configs/scanners/`, `configs/presets/`, `configs/legacy/`) via `make scan-audit`, and gate network tests behind markers/env vars.
3. **Stable export envelope + run scoping**: implemented (`{meta,data}` envelope + `export/<run_id>/...`) to prevent cross-run leakage; consumers fall back to legacy filename parsing when needed.
4. **Standardized scan runner**: implemented via `scripts/compose_pipeline.py` and `make scan-run` (manifest-driven pipelines with interval + ingestion depth overrides).
5. **Selector refactor**: `build_payloads()` now matches real execution; remaining work is splitting selector internals into modules (config loader, payload builder, post-filters, normalization, export).
6. **Config DRY**: introduce layered presets and additive list merges (`filters_add`, `columns_add`, etc.) to reduce duplication without breaking existing configs.
