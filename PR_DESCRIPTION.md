# Pull Request: Add Historical OHLCV Data Extractor

## Summary

This PR adds a new `OHLCVExtractor` class to the `tradingview_scraper` package, providing a convenient way to fetch historical OHLCV (Open, High, Low, Close, Volume) data from TradingView with customizable timeframes and bar counts.

## Motivation

While the existing `RealTimeData` class provides excellent streaming capabilities for real-time data, there was no straightforward way to fetch historical OHLCV data on-demand without maintaining a persistent WebSocket connection. This extractor fills that gap by providing:

- **On-demand historical data retrieval** without persistent connections
- **Batch processing** for multiple symbols
- **Rich metadata** including formatted timestamps and percentage changes
- **Flexible timeframe support** (1m to 1M)
- **Debug mode** for troubleshooting
- **Export capabilities** to JSON files

## Changes

### New Files

1. **`tradingview_scraper/symbols/stream/ohlcv_extractor.py`**
   - Main implementation of the `OHLCVExtractor` class
   - Extends `RealTimeData` with on-demand data fetching capabilities
   - Includes convenience functions `get_ohlcv_json()` and `get_multiple_ohlcv_json()`
   - Implements robust error handling and timeout management

2. **`examples/ohlcv_extractor_example.py`**
   - Comprehensive usage examples
   - Demonstrates single symbol extraction
   - Shows batch processing for multiple symbols
   - Includes statistical analysis examples
   - Compares different timeframes

### Modified Files

1. **`tradingview_scraper/symbols/stream/__init__.py`**
   - Added exports for `OHLCVExtractor`, `get_ohlcv_json`, and `get_multiple_ohlcv_json`

2. **`README.md`**
   - Added new section "6.1. Historical OHLCV Data Extraction"
   - Comprehensive documentation with code examples
   - Output format specifications
   - Error handling guidelines

## Features

### Core Functionality

- **Single Symbol Extraction**: Fetch historical bars for any symbol
- **Multiple Symbol Batch Processing**: Efficiently retrieve data for multiple symbols
- **Customizable Timeframes**: Support for 1m, 5m, 15m, 30m, 1h, 2h, 4h, 1D, 1W, 1M
- **Configurable Bar Count**: Request any number of historical bars
- **Timeout Control**: Prevent hanging requests with configurable timeouts
- **Debug Mode**: Optional verbose logging for troubleshooting

### Data Format

Each bar includes:
- Unix timestamp
- ISO formatted datetime
- Separate date and time strings
- OHLCV values
- Calculated percentage change

### Error Handling

- WebSocket connection errors
- Timeout handling
- Server error detection
- Graceful degradation with detailed error messages

## Usage Examples

### Quick Start

```python
from tradingview_scraper.symbols.stream import get_ohlcv_json

# Fetch 10 daily bars for Bitcoin
data = get_ohlcv_json(
    symbol="BINANCE:BTCUSDT",
    timeframe="1D",
    bars_count=10
)

if data['success']:
    print(f"Retrieved {data['bars_received']} bars")
    print(f"Latest close: ${data['data'][-1]['close']:,.2f}")
```

### Multiple Symbols

```python
from tradingview_scraper.symbols.stream import get_multiple_ohlcv_json

symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:ADAUSDT"]
results = get_multiple_ohlcv_json(symbols=symbols, timeframe="1h", bars_count=5)

print(f"Successful: {results['successful_symbols']}/{results['total_symbols']}")
```

### Advanced Usage

```python
from tradingview_scraper.symbols.stream import OHLCVExtractor

extractor = OHLCVExtractor(debug_mode=True)
result = extractor.get_ohlcv_data(
    symbol="BINANCE:ETHUSDT",
    timeframe="15m",
    bars_count=20,
    timeout=45
)
```

## Technical Details

### Architecture

The `OHLCVExtractor` class:
- Extends the existing `RealTimeData` class
- Uses relative imports for clean package integration
- Creates fresh WebSocket connections per request to avoid state issues
- Implements proper cleanup in `finally` blocks

### Design Decisions

1. **Per-Request Connections**: Each data request creates a new WebSocket connection to ensure clean state and avoid connection reuse issues.

2. **Timeout Protection**: Default 30-second timeout prevents hanging requests, with configurable override.

3. **Debug Mode**: Logging is silenced by default for production use, but can be enabled for troubleshooting.

4. **Convenience Functions**: Top-level functions (`get_ohlcv_json`, `get_multiple_ohlcv_json`) provide simple interfaces for common use cases.

## Testing

The integration has been tested with:
- ✅ Single symbol extraction
- ✅ Multiple symbol batch processing
- ✅ Various timeframes (1m, 1h, 1D)
- ✅ Error handling scenarios
- ✅ Import structure verification

## Backward Compatibility

This PR is **fully backward compatible**:
- No changes to existing functionality
- Only adds new exports to `stream` module
- Existing code continues to work without modification

## Documentation

- ✅ Comprehensive README section added
- ✅ Inline code documentation with docstrings
- ✅ Complete usage examples provided
- ✅ Error handling guidelines included

## Future Enhancements

Potential future improvements:
- Connection pooling for batch requests
- Caching layer for frequently requested data
- Support for custom indicators alongside OHLCV
- Async/await interface for concurrent requests

## Checklist

- [x] Code follows project style guidelines
- [x] Documentation added to README
- [x] Usage examples provided
- [x] Backward compatibility maintained
- [x] Error handling implemented
- [x] No breaking changes

## Related Issues

This PR addresses the need for on-demand historical OHLCV data extraction, complementing the existing real-time streaming capabilities.
