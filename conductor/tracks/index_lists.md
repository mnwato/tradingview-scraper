# Index Lists (SP500 / Nasdaq-100)

Purpose: generate and refresh TradingView-ready symbol lists for SP500 and Nasdaq-100, used by US stocks/ETF base universes.

Sources & fallback order
1) TradingView screener (index code SPX/NDX; currently returns empty for index filter)
2) Slickcharts tables (primary active source)
3) ETF holdings CSV/HTML (IVV for SP500, QQQ page for NDX)
4) Wikipedia tables (last resort)

Script
- `scripts/update_index_lists.py`
- Outputs: `data/index/sp500_symbols.txt`, `data/index/nasdaq100_symbols.txt` (one symbol per line, TradingView format when resolvable)
- Mapping: uses `data/lakehouse/symbols.parquet` to map tickers to exchange-prefixed symbols; falls back to raw tickers if no match.

Run
```bash
uv run scripts/update_index_lists.py
```
Flags: `--sp500-file`, `--nasdaq100-file`, `--symbols-parquet`, `--page-size`, `--max-rows`.

Integration
- `configs/us_stocks_base_universe.yaml` includes the generated lists via `include_symbol_files` (relative `../data/index/...`).
- `configs/us_etf_base_universe.yaml` has the same hook.
- After updating lists, rerun US scans:
```bash
uv run -m tradingview_scraper.futures_universe_selector --config configs/us_stocks_trend_momentum.yaml --export json
uv run -m tradingview_scraper.futures_universe_selector --config configs/us_stocks_trend_momentum_short.yaml --export json
uv run -m tradingview_scraper.futures_universe_selector --config configs/us_etf_trend_momentum.yaml --export json
uv run -m tradingview_scraper.futures_universe_selector --config configs/us_etf_trend_momentum_short.yaml --export json
uv run scripts/summarize_results.py
```

Validation
- Expected counts: ~500 for SP500, ~100 for Nasdaq-100. The script prints source and count per index.
- If counts are low, check network/HTTP status; script will automatically fall back to next source.

Troubleshooting
- 403/blocked: rerun; uses random UA, but you may need to retry or switch network.
- Empty screener results: index filter likely unsupported; rely on slickcharts/ETF/wiki fallbacks.
- Missing symbols: ensure `symbols.parquet` is up to date for exchange prefix mapping.
