# Metadata Catalog Schema and Usage Guidelines

## Overview

This document describes the metadata catalog system for TradingView scraper, which manages instrument definitions for exchanges and symbols in the data lakehouse.

## Architecture

### Components

1. **MetadataCatalog** (`data/lakehouse/symbols.parquet`)
   - Symbol-level metadata with SCD Type 2 versioning
   - Point-in-time (PIT) lookup capabilities
   - Change detection and validation

2. **ExchangeCatalog** (`data/lakehouse/exchanges.parquet`)
   - Exchange-level metadata and defaults
   - Used for timezone and market session defaults

3. **MetadataService**
   - High-level interface for symbol discovery and resolution
   - Future support for hybrid data sources (TradingView + CCXT)

## Design Requirements

- **PIT + survivorship**: Backtests MUST query `MetadataCatalog.get_instrument(..., as_of=timestamp)` and MUST NOT rely on the latest "current" metadata for historical simulation.
- **Profile is persisted**: `profile` is a required, versioned field in `symbols.parquet` (used for market-aware calendars, gap detection, and survivorship-safe backtests).
- **API-synced where available**: Values returned by the TradingView `Overview` API (e.g. `timezone`, `pricescale`, `minmov`, `type`) are authoritative; defaults apply only when the API returns `None`.
- **Incremental updates**: Build on existing catalogs using SCD Type 2 upserts; do not delete catalog files in production/backtesting contexts.

## Schema Definition

### Symbol Metadata Schema

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| symbol | str | ✓ | Full symbol identifier (e.g., "BINANCE:BTCUSDT") |
| exchange | str | ✓ | Exchange name (e.g., "BINANCE", "BYBIT") |
| base | str | ✗ | Base currency (e.g., "BTC") |
| quote | str | ✗ | Quote currency (e.g., "USDT") |
| type | str | ✓ | Instrument type ("spot", "swap", "futures", "stock", "fund", "commodity", "forex", "index", "dr") |
| profile | str | ✓ | Persisted DataProfile enum ("CRYPTO", "EQUITY", "FUTURES", "FOREX", "UNKNOWN") used for market calendars and PIT-safe backtests |
| subtype | str | ✗ | Additional classification (e.g., "perpetual") |
| description | str | ✗ | Human-readable description |
| sector | str | ✗ | Economic sector (for stocks) |
| industry | str | ✗ | Industry classification (for stocks) |
| country | str | ✗ | Country/region of exchange |
| pricescale | int | ✓ | Price precision (decimal places) |
| minmov | int | ✓ | Minimum price movement |
| tick_size | float | ✗ | Calculated tick size (minmov / pricescale) |
| lot_size | float | ✗ | Contract lot size (for execution) |
| contract_size | float | ✗ | Contract size (for execution) |
| timezone | str | ✓ | Exchange timezone (e.g., "UTC", "America/New_York") |
| session | str | ✗ | Trading session ("24x7", "09:30-16:00", etc.) |
| active | bool | ✓ | Currently active instrument |
| valid_from | datetime | ✓ | Record validity start (SCD Type 2) |
| valid_until | datetime | ✗ | Record validity end (null = currently active) |
| updated_at | datetime | ✓ | Last update timestamp |

### Exchange Metadata Schema

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| exchange | str | ✓ | Exchange identifier |
| country | str | ✓ | Country/region |
| timezone | str | ✓ | Primary timezone |
| is_crypto | bool | ✓ | Crypto exchange flag |
| description | str | ✓ | Exchange description |
| updated_at | datetime | ✓ | Last update timestamp |

## Market Resilience & Health

### Data Profiles
Assets are categorized into `DataProfile` groups to enable market-aware gap detection:
- **CRYPTO**: 24/7 trading. No expected gaps.
- **EQUITY**: M-F 09:30-16:00 ET. Skips weekends and US holidays.
- **FUTURES**: Sun-Fri. Specific daily breaks (e.g., 17:00-18:00 ET).
- **FOREX**: Sun 17:00 ET - Fri 17:00 ET.

### Health Statuses
The portfolio data validation pipeline (`make validate`) assigns one of the following statuses.
For metadata catalogs (symbols/exchanges), use `make meta-validate` (refresh + offline audits) and `make meta-audit` (includes online parity sampling).
- **OK**: Continuous data with no gaps.
- **OK (MARKET CLOSED)**: Gaps found, but they match weekends or known US market holidays.
- **DEGRADED (GAPS)**: Unexpected data holes during active trading hours.
- **STALE**: Data has not been updated within the last 72 hours.
- **MISSING**: No local storage file found for the candidate.

### Holiday Management
The system uses a built-in US Market Holiday list (`get_us_holidays`) to filter false-positive gaps for Equities and Futures.

## Data Flow

### Building Catalog

```bash
# Makefile shortcuts (recommended)
make meta-refresh
make meta-validate
make meta-audit

# Refresh all active symbols from the existing catalog (preserves PIT history)
uv run scripts/build_metadata_catalog.py --from-catalog --catalog-path data/lakehouse/symbols.parquet

# Or build from a candidates file (expects a JSON list of objects with `symbol`)
uv run scripts/build_metadata_catalog.py --candidates-file /tmp/candidates.json

# If your export uses {meta,data}, extract the list first:
# jq '.data' export/<run_id>/universe_selector_*.json > /tmp/candidates.json

# Or specific symbols
uv run scripts/build_metadata_catalog.py --symbols BINANCE:BTCUSDT BYBIT:ETHUSDT
```

### Auditing Catalog

```bash
# Makefile shortcuts
make meta-audit-offline
make meta-audit

# Full audit (includes online parity sample)
uv run scripts/audit_metadata_catalog.py

# Timezone audit
uv run scripts/audit_metadata_timezones.py

# Point-in-time audit
uv run scripts/audit_metadata_pit.py
```

### Cleaning Catalog

```bash
# Fix data types and duplicates
uv run scripts/cleanup_metadata_catalog.py
```

## Usage Examples

### Basic Symbol Lookup

```python
from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

catalog = MetadataCatalog()
metadata = catalog.get_instrument("BINANCE:BTCUSDT")

if metadata:
    print(f"Tick size: {metadata['tick_size']}")
    print(f"Timezone: {metadata['timezone']}")
```

### Point-in-Time Lookup

```python
from datetime import datetime
from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

catalog = MetadataCatalog()
# Get metadata as of yesterday
yesterday = datetime.now().replace(hour=0, minute=0, second=0)
historical_meta = catalog.get_instrument("BINANCE:BTCUSDT", as_of=yesterday)
```

### Exchange Metadata

```python
from tradingview_scraper.symbols.stream.metadata import ExchangeCatalog

ex_catalog = ExchangeCatalog()
exchange_info = ex_catalog.get_exchange("BINANCE")

if exchange_info:
    print(f"Timezone: {exchange_info['timezone']}")
    print(f"Is Crypto: {exchange_info['is_crypto']}")
```

## Validation Rules

### Symbol Validation

1. **Required Fields**: symbol, exchange, type, profile must be present and non-empty
2. **Numeric Fields**: pricescale, minmov must be positive integers
3. **Tick Size**: Calculated as minmov / pricescale, must be positive
4. **Timezone**: Must be valid IANA timezone or "UTC"
5. **Session**: Use API value when present; otherwise resolve from exchange/profile defaults. "24x7" is reserved for crypto.

### Exchange Validation

1. **Required Fields**: exchange, country, timezone must be present
2. **Timezone**: Must be valid IANA timezone
3. **Unique**: Exchange names must be unique

## Best Practices

### 1. Data Consistency

- Always use proper data types (int for pricescale/minmov)
- Validate timezone names against IANA database
- Use consistent exchange names across symbols and exchange catalog

### 2. Change Detection

- Only update records when critical fields change
- Maintain SCD Type 2 versioning for audit trail
- Include timestamps for change tracking

### 3. Performance

- Use point-in-time lookups for historical queries
- Index catalog on symbol and valid_from/valid_until fields
- Cache frequently accessed exchange metadata

### 4. Error Handling

- Validate input data before processing
- Log warnings for non-critical issues
- Skip records with critical validation errors

## Maintenance Schedule

### Daily
- Run audit scripts to check for inconsistencies
- Update active symbols with latest TradingView data

### Weekly  
- Clean up duplicate records
- Validate timezone and session data
- Update exchange metadata if needed

### Monthly
- Review and archive old inactive records
- Update exchange metadata defaults
- Performance optimization and indexing review

## Integration Points

### Data Lakehouse
- Catalog files stored in `data/lakehouse/` directory
- Parquet format for efficient querying
- Compatible with pandas and pyarrow

### TradingView API
- Symbol metadata fetched via Overview API (authoritative when present)
- Exchange defaults resolved via `ExchangeCatalog` (bootstrapped from `DEFAULT_EXCHANGE_METADATA`)
- Real-time validation against API responses (spot checks)

### Future CCXT Integration
- MetadataService designed for hybrid sourcing
- Exchange metadata can be enriched with CCXT data
- Symbol discovery across multiple exchanges

## Troubleshooting

### Common Issues

1. **Type Mismatches**: Run cleanup script to fix data types
2. **Missing Timezones**: Check exchange metadata defaults  
3. **Duplicate Symbols**: Use cleanup script to remove duplicates
4. **Invalid Tick Sizes**: Recalculate with cleanup script

### Debug Commands

```bash
# Makefile shortcuts
make meta-stats
make meta-validate
make meta-audit
make meta-explore

# Validate specific symbol
uv run scripts/validate_symbol.py BINANCE:BTCUSDT

# Refresh all active symbols from existing symbols.parquet (preserves PIT history)
uv run scripts/build_metadata_catalog.py --from-catalog --catalog-path data/lakehouse/symbols.parquet

# Avoid deleting `symbols.parquet` / `exchanges.parquet` in production/backtesting contexts:
# it destroys PIT history and can introduce survivorship/look-ahead bias.
```

## Schema Evolution

### Versioning
- Schema changes should maintain backward compatibility
- New fields added with nullable types initially
- Document breaking changes in release notes

### Migration
- Use cleanup scripts for data type changes
- Implement gradual rollouts for new features
- Maintain archive of old catalog versions
