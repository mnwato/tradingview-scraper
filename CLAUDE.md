# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradingView Scraper is a Python library for scraping trading data, ideas, news, and real-time market information from TradingView.com. The package supports both HTTP scraping and WebSocket-based real-time data streaming.

## Development Commands

### Installation and Setup (UV Native)
```bash
# Prepare environment with all core and optional backends
uv sync --all-extras

# Update lockfile after pyproject.toml changes
uv lock

# Export requirements for non-uv environments (compatibility)
uv export --no-dev --format requirements-txt > requirements.txt
uv export --extra dev --format requirements-txt > dev-requirements.txt
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_ideas.py
```

### Code Quality
```bash
# Lint with ruff
uv run ruff check .

# Format with ruff
uv run ruff format .

# Type checking
uv run ty
```

### Portfolio Backtesting (Tournament Matrix)
```bash
# Run the multi-engine, multi-profile tournament
uv run scripts/backtest_engine.py --tournament

# Generate unified quantitative reports
TV_RUN_ID=<id> uv run scripts/generate_reports.py
```

### Analytical Reports
```bash
# Generate final prettified dashboard
make report

# Deeper cluster hierarchy analysis (Selected or Raw universe)
uv run scripts/analyze_clusters.py --mode raw
```

## Architecture

### Core Module Structure
- `regime.py` - Advanced multi-factor detector (Entropy, DWT, Vol Clustering).
- `risk.py` - Barbell optimizer and tail risk (CVaR) auditing.
- `pipeline.py` - Unified orchestrator for Discovery -> Alpha -> Risk flow.
- `bond_universe_selector.py` - Wrapper for US-listed Bond ETF discovery.

**`scripts/`** - Production Pipeline Stages
- `select_top_universe.py` - Aggregates raw pool with canonical venue merging.
- `natural_selection.py` - Statistical pruning via hierarchical clustering.
- `optimize_clustered_v2.py` - Unified factor-based optimizer with fragility penalties.
- `generate_portfolio_report.py` - Prettified Markdown dashboard with visual bars.
- `display_portfolio_dashboard.py` - Interactive Rich terminal Implementation Dashboard.
- `monitor_cluster_drift.py` - Temporal stability tracking for risk buckets.
- `detect_hedge_anchors.py` - Automated discovery of insurance/diversification assets.

### Deployment & Maintenance
- **Data Integrity**: Uses a tiered self-healing cycle (`Pass 1: 60d` -> `Natural Selection` -> `Pass 2: 200d`).
- **Risk Control**: Cluster-aware allocation with strictly enforced 25% caps and CVaR-penalized objectives.
- **Alpha Alignment**: Hybrid internal distribution using a blend of Momentum and Stability.
- **Decision Trail**: Persistent logging of every selection decision in `selection_audit.json`.

## Key Design Patterns


#### Export Pattern
All main scraper classes follow a consistent pattern:
- Constructor accepts `export_result` (bool) and `export_type` ('json'|'csv')
- `_export()` method handles file saving via `save_json_file()` or `save_csv_file()`
- Data always returned as Python dict/list regardless of export settings

#### WebSocket Streaming Architecture
The streaming system has two approaches:

1. **Simple Streaming** (`RealTimeData` in `price.py`):
   - Returns Python generators that yield real-time packets
   - Use `get_ohlcv()` for OHLC data or `get_latest_trade_info()` for watchlist data
   - No indicator support, no authentication required

2. **Advanced Streaming** (`Streamer` in `streamer.py`):
   - Supports both OHLC and indicators simultaneously
   - Can export historical data by setting `export_result=True`
   - Requires JWT token for indicator access via `websocket_jwt_token` parameter
   - Returns generator for streaming or dict for historical export

#### Session Management Pattern
WebSocket scrapers use session-based communication:
- `_add_symbol_to_sessions()` - Registers symbols to quote/chart sessions
- `_add_indicator()` - Adds indicator studies to chart session
- Session IDs generated via `StreamHandler.generate_session()` using random strings

### Data Flow

#### HTTP Scraping Flow
```
User Request → Scraper Class (Ideas/Indicators/News/Calendar)
  → HTTP Request with user-agent
  → Response Parsing (BeautifulSoup/JSON)
  → Data Normalization
  → Optional Export (CSV/JSON)
  → Return Python dict/list
```

#### WebSocket Streaming Flow
```
User Request → Streamer/RealTimeData
  → StreamHandler establishes WebSocket connection
  → Send session setup messages (quote_create_session, chart_create_session)
  → Add symbols and indicators to sessions
  → Listen for packets (timescale_update, du, qsd, etc.)
  → Parse and serialize data
  → Yield to generator or export to file
```

### Important Implementation Details

#### Ideas Scraping
- Uses JSON API for both popular and recent ideas via TradingView's component-data-only endpoint
- Concurrent page scraping with ThreadPoolExecutor (3 workers) to avoid rate limiting
- Cookie authentication support for captcha avoidance (set via `TRADINGVIEW_COOKIE` env var)
- Automatic error handling for captcha challenges and network issues
- Structured output with consistent field mapping from API response

#### Indicators
- Timeframe handling: indicators are modified with `|{timeframe}` suffix for non-daily timeframes
- Scanner API endpoint: `https://scanner.tradingview.com/symbol`
- Validation against `indicators.txt` and `exchanges.txt` before making requests

#### WebSocket Protocol
- Custom TradingView protocol with `~m~{length}~m~{message}` framing
- Heartbeat messages (`~h~{number}`) must be echoed back
- Messages are JSON-RPC style with method names like "quote_add_symbols", "create_series"
- Packet types identified by `m` field: "du" (data update), "qsd" (quote data), "timescale_update" (OHLC)

#### OHLC Timeframe Handling
- WebSocket streaming returns 1-minute candles by default
- Timeframe conversion is not currently implemented in the streamer
- Raw 1-minute data is exported as-is

## Testing Strategy

Tests use pytest with both mocking and real API calls. Key patterns:
- Mocked tests use `@mock.patch('tradingview_scraper.symbols.ideas.requests.get')` for HTTP mocking
- Real API tests validate end-to-end functionality with live TradingView data
- Threading tests verify concurrent requests don't hit rate limits
- Test both success cases and error handling (invalid symbols, no data, captcha challenges, etc.)

When adding tests:
- Follow the fixture pattern (see `test_ideas.py:17`)
- Test both valid data and edge cases (empty results, invalid parameters)
- For WebSocket tests, mock the connection but test the parsing logic

## Version and Dependencies

- Python 3.8+ required
- Key dependencies: setuptools, requests==2.32.4, pandas>=2.0.3, beautifulsoup4>=4.12.3, pydantic>=2.8.2, websockets>=13.1, websocket-client>=1.8.0
- Current version: 0.4.19 (see setup.py:19)

## CI/CD

GitHub Actions workflows:
- **python-app.yml**: Runs on push/PR to main, executes ruff linting and pytest
- **pylint.yml**: Runs pylint on all Python files for Python 3.8 and 3.9
- **release.yml**: Handles PyPI releases
- **docs.yml**: Builds and publishes documentation

## Git Commit Guidelines

When creating git commits:
- **NEVER** add "Co-Authored-By: Claude" or similar AI attribution to commit messages
- **NEVER** add "Generated with Claude Code" or similar phrases to commit messages
- Keep commit messages focused on what changed and why
- Follow conventional commit format: `type: description`
- Use these types: feat, fix, docs, test, refactor, chore

## Common Patterns to Follow

When adding new scrapers:
1. Inherit common patterns: `__init__` with export params, `scrape()` method, `_export()` helper
2. Use `generate_user_agent()` for all HTTP requests
3. Add validation for parameters (exchange, symbol, timeframe) against data files
4. Return consistent dict structure with descriptive keys
5. Handle errors gracefully with try/except and meaningful error messages
6. Add corresponding test file in `tests/` with pytest fixtures
