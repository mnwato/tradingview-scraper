# Design Document: Composable Layered Pipelines (L0-L4)

## 1. Overview
The Quantitative Portfolio Platform is transitioning from a flat, redundant configuration model to a hierarchical building-block architecture. This allows for rapid composition of scanners and ingestion pipelines while maintaining strict institutional data standards across all asset classes and intervals.

## 2. Layered Architecture

### L0: Universe Foundation (`configs/base/universes/`)
Defines the absolute broad pool of candidates.
- **Index Constituents**: S&P 500, NASDAQ 100, Dow 30.
- **High-Integrity Lists**: Uses `include_symbol_files` pointing to manual lists (e.g., `../data/index/sp500_symbols.txt`) to bypass unreliable provider index filters and avoid HTTP 400 errors.
- **Exchange Rankings**: Binance Top 50, Bybit Top 50 (ranked by 24h Volume/Market Cap).

### L1: Institutional Hygiene (`configs/base/hygiene/`)
Global technical and liquidity filters applied to all institutional runs.
- **Technical**: ADX > 20, minimum ATR thresholds.
- **Liquidity**: Minimum `Value.Traded` (e.g., > $10M USD/day).
- **Price**: Penny stock exclusions (e.g., price > $1.00).

### L2: Asset Templates (`configs/base/templates/`)
Domain-specific rules for market sessions and data handling.
- **Session Normalization**: Sunday-start offsets (+4h for Forex/Futures between 20:00-23:59 UTC).
- **Calendar Mapping**: Mapping TV exchanges to `exchange_calendars` (e.g., EUREX -> `XFRA`).
- **Provider Priority**: Preferred quotes (USDT vs USDC) and brokers.

### L3: Strategy Blocks (`configs/base/strategies/`)
Specific technical logic for finding alpha.
- **Trend Following**: Momentum horizons (1M, 3M), confirmation rules.
- **Mean Reversion**: RSI, Bollinger Band, and oversold/overbought logic.
- **Multi-Timeframe (MTF)**: Filter alignment across Daily/Weekly/Monthly.

### L4: Pipeline Entry (`configs/scanners/`)
The composition root that flattens L0-L3 into a runnable scanner.
- Uses the `base_preset` recursive logic to inherit layers.
- Defines the `timeframe` (interval) for the run.

## 3. Integrated Workflow Specification

### Discovery -> Ingestion Stream
1.  **Compose**: Resolve recursive `base_preset` into a single `SelectorConfig`.
2.  **Scan**: Execute `Screener.screen()` against TradingView.
3.  **Validate**: Apply Market-Day normalization to discovered symbols.
4.  **Ingest**: Pass symbols and `timeframe` to `PersistentLoader`.
    - **Tagging**: Each symbol is tagged with `strategy_name` (L4) and `asset_class` (L2).
    - **Handoff**: Discovered symbols are merged into `data/lakehouse/portfolio_candidates_raw.json`.
5.  **Backfill**: Fetch secular history (up to 8,500 candles for intraday, 3,050 for daily).
6.  **Audit**: Run Step 8 Health Audit using Market-Day normalization.

## 4. Manifest Schema Updates
The `manifest.json` will be updated to support:
- `pipelines`: Named sequences of L4 scanner configurations.
- `global_lookback`: Interval-aware depth settings.
- `strict_health`: Block downstream optimization if ingestion fails.

## 5. Multi-Interval Support
- **Supported Intervals**: `1m, 5m, 15m, 1h, 4h, 1d, 1w, 1M`.
- **Interval Propagation**: The scanner `timeframe` key automatically dictates the loader's `interval`.
