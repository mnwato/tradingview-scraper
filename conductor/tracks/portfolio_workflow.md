# Portfolio Workflow (Scans → Prep → Optimize)

This playbook shows the end-to-end steps: run local + crypto scanners, summarize outputs, prep portfolio data, rank/build the universe, and optimize across profiles (min variance, risk parity à la Ray Dalio, and antifragile barbell à la Taleb).

## 1) Run scanners
```
# Recommended: run-scoped exports
RUN_ID=20251228-120000 make scan-all

# Or run individual groups
TV_EXPORT_RUN_ID=20251228-120000 bash scripts/run_local_scans.sh
TV_EXPORT_RUN_ID=20251228-120000 bash scripts/run_crypto_scans.sh
```
- Outputs land in `export/<run_id>/` as `universe_selector_*` JSONs using a `{meta,data}` envelope.
- Portfolio artifacts land in `artifacts/summaries/runs/<TV_RUN_ID>/` (Makefile sets `TV_RUN_ID` to the workflow `RUN_ID`) and `artifacts/summaries/latest` points to the last successful finalized run.

## 2) Summarize scan results
```
# Defaults to the newest `export/<run_id>/` if TV_EXPORT_RUN_ID is unset
TV_EXPORT_RUN_ID=20251228-120000 uv run scripts/summarize_results.py
TV_EXPORT_RUN_ID=20251228-120000 uv run scripts/summarize_crypto_results.py
```
- Produces console summaries for all asset classes.

## 2b) Forex base universe audit (optional)
```
# Fast: liquidity report only
RUN_ID=20251228-120000 make forex-analyze-fast

# Full: backfill + gap-fill + data health + clusters
RUN_ID=20251228-120000 BACKFILL=1 GAPFILL=1 FOREX_LOOKBACK_DAYS=365 make forex-analyze
```
- Excludes IG-only singleton pairs by default and writes `artifacts/summaries/runs/<RUN_ID>/forex_universe_report.md` plus `forex_universe_data_health.csv` and hierarchical clustering artifacts.

## 3) Prepare portfolio data (fetch/backfill/gap-fill + returns)
```
# Tune batch/limits as needed; backfill/gapfill capped with timeouts/limits
PORTFOLIO_BATCH_SIZE=5 \
PORTFOLIO_LOOKBACK_DAYS=100 \
PORTFOLIO_BACKFILL=1 \
PORTFOLIO_GAPFILL=0 \
uv run scripts/prepare_portfolio_data.py
```
- Env knobs: `PORTFOLIO_BATCH_SIZE`, `PORTFOLIO_LOOKBACK_DAYS`, `PORTFOLIO_BACKFILL`, `PORTFOLIO_GAPFILL` (set 0 to skip backfill/gapfill).
- **Stabilization Note:** Backfill and Gap-fill now have strict caps (120s backfill timeout, 60s gap-fill timeout, 2010 legacy cutoff). If the script hangs or takes too long, set `PORTFOLIO_GAPFILL=0`.
- Uses `data/lakehouse/portfolio_candidates.json` (built from selectors) and writes `data/lakehouse/portfolio_returns.pkl` plus sidecar metadata.

## 4) Rank/build universe for portfolio
- Universe comes from `data/lakehouse/portfolio_candidates.json` (produced by the selectors + `select_top_universe.py`).
- `prepare_portfolio_data.py` loads prices/returns for those candidates; check the summary logs for any symbols dropped due to missing history.

## 5) Optimize portfolios (multiple profiles)
Recommended (cluster-aware optimization; includes an antifragile barbell profile):
```
make optimize-v2
```
- Writes `data/lakehouse/portfolio_optimized_v2.json` and updates `data/lakehouse/selection_audit.json`.

To generate the operator-ready Markdown outputs:
```
make report
```

## Quick daily sequence
Recommended (end-to-end, incremental):
```
# Auto-generates a run id if RUN_ID is unset
make run-daily

# Or pin a run id for reproducibility
RUN_ID="$(date +%Y%m%d-%H%M%S)" make run-daily
```
- Outputs:
  - Exports: `export/<TV_EXPORT_RUN_ID>/...`
  - Artifacts (this run): `artifacts/summaries/runs/<TV_RUN_ID>/...`
  - Latest finalized: `artifacts/summaries/latest` (symlink)
