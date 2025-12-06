# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradingView Scraper is a Python library for scraping trading data, ideas, news, and real-time market information from TradingView.com. The package supports both HTTP scraping and WebSocket-based real-time data streaming.

## Development Commands

### Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ideas.py
pytest tests/test_indicators.py
pytest tests/test_realtime_price.py

# Run tests with verbose output
pytest -v
```

### Code Quality
```bash
# Lint with flake8 (used in CI)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Run pylint (used in CI)
pylint $(git ls-files '*.py')
```

### Building Documentation
```bash
cd docs
make html
```

## Architecture

### Core Module Structure

The package is organized into the following key components:

**`tradingview_scraper/symbols/`** - Main data scraping modules
- `ideas.py` - Scrapes trading ideas from TradingView symbol pages
- `technicals.py` - Fetches technical indicators via TradingView scanner API
- `news.py` - Scrapes news headlines and content for symbols
- `cal.py` - Scrapes calendar events (earnings, dividends)
- `utils.py` - Shared utilities for file export, user agent generation, validation
- `exceptions.py` - Custom exception classes

**`tradingview_scraper/symbols/stream/`** - Real-time WebSocket streaming
- `streamer.py` - Main `Streamer` class for OHLCV and indicator streaming with export capabilities
- `price.py` - `RealTimeData` class for simple OHLCV and watchlist streaming
- `stream_handler.py` - Low-level WebSocket connection and message handling
- `utils.py` - WebSocket utilities, symbol validation, indicator metadata fetching

**`tradingview_scraper/utils/`** - Shared utilities
- Currently empty, reserved for future shared utilities

**`tradingview_scraper/data/`** - Static configuration files
- `indicators.txt` - List of supported indicator names
- `exchanges.txt` - List of supported exchanges
- `timeframes.json` - Timeframe mappings
- `languages.json`, `areas.json`, `news_providers.txt` - News scraping configurations

### Key Design Patterns

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
- **python-app.yml**: Runs on push/PR to main, executes flake8 linting and pytest
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
