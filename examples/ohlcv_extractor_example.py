"""
Example usage of the OHLCV Extractor module.

This module demonstrates how to use the OHLCVExtractor class to fetch
historical OHLCV (Open, High, Low, Close, Volume) data from TradingView.
"""

from tradingview_scraper.symbols.stream import get_ohlcv_json, get_multiple_ohlcv_json, OHLCVExtractor

def example_single_symbol():
    """Example 1: Fetch OHLCV data for a single symbol using convenience function."""
    print("=" * 60)
    print("Example 1: Single Symbol - BTCUSDT (1D, 10 bars)")
    print("=" * 60)
    
    result = get_ohlcv_json(
        symbol="BINANCE:BTCUSDT",
        timeframe="1D",
        bars_count=10,
        save_to_file=True,
        debug=True
    )
    
    if result['success']:
        print(f"\n✅ Success! Retrieved {result['bars_received']} bars")
        print(f"Latest bar: {result['data'][-1]['date']} - Close: ${result['data'][-1]['close']:,.2f}")
    else:
        print(f"\n❌ Error: {result['metadata']['error']}")
    
    return result


def example_multiple_symbols():
    """Example 2: Fetch OHLCV data for multiple symbols."""
    print("\n" + "=" * 60)
    print("Example 2: Multiple Symbols - Crypto Portfolio")
    print("=" * 60)
    
    symbols = [
        "BINANCE:BTCUSDT",
        "BINANCE:ETHUSDT",
        "BINANCE:ADAUSDT"
    ]
    
    result = get_multiple_ohlcv_json(
        symbols=symbols,
        timeframe="1h",
        bars_count=5,
        save_to_file=True,
        debug=False
    )
    
    print(f"\n📊 Processed {result['total_symbols']} symbols")
    print(f"✅ Successful: {result['successful_symbols']}")
    print(f"❌ Failed: {result['failed_symbols']}")
    
    if result['errors']:
        print("\nErrors:")
        for symbol, error in result['errors'].items():
            print(f"  - {symbol}: {error}")
    
    return result


def example_class_usage():
    """Example 3: Using the OHLCVExtractor class directly."""
    print("\n" + "=" * 60)
    print("Example 3: Direct Class Usage - Custom Configuration")
    print("=" * 60)
    
    # Create extractor instance with debug mode
    extractor = OHLCVExtractor(debug_mode=True)
    
    # Fetch data with custom timeout
    result = extractor.get_ohlcv_data(
        symbol="BINANCE:ETHUSDT",
        timeframe="15m",
        bars_count=20,
        timeout=45
    )
    
    if result['success']:
        print(f"\n✅ Retrieved {result['bars_received']} bars in {result['metadata']['processing_time_seconds']}s")
        
        # Calculate some statistics
        closes = [bar['close'] for bar in result['data']]
        avg_close = sum(closes) / len(closes)
        max_close = max(closes)
        min_close = min(closes)
        
        print(f"\n📈 Statistics:")
        print(f"  Average Close: ${avg_close:,.2f}")
        print(f"  Max Close: ${max_close:,.2f}")
        print(f"  Min Close: ${min_close:,.2f}")
    else:
        print(f"\n❌ Error: {result['metadata']['error']}")
    
    return result


def example_different_timeframes():
    """Example 4: Comparing different timeframes."""
    print("\n" + "=" * 60)
    print("Example 4: Different Timeframes - Same Symbol")
    print("=" * 60)
    
    symbol = "BINANCE:BTCUSDT"
    timeframes = ["1h", "4h", "1D"]
    
    for tf in timeframes:
        result = get_ohlcv_json(
            symbol=symbol,
            timeframe=tf,
            bars_count=3,
            debug=False
        )
        
        if result['success']:
            latest = result['data'][-1]
            print(f"\n{tf:>3} - Close: ${latest['close']:>10,.2f} | Change: {latest['change_percent']:>6.2f}%")
        else:
            print(f"\n{tf:>3} - Error: {result['metadata']['error']}")


if __name__ == "__main__":
    print("\n🔧 OHLCV Extractor - Usage Examples")
    print("=" * 60)
    
    # Run examples
    example_single_symbol()
    example_multiple_symbols()
    example_class_usage()
    example_different_timeframes()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)
