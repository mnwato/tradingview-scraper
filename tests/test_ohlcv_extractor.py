"""
Tests for the OHLCV Extractor module.
"""

import unittest
import sys
import os

# Add parent directory to path to allow importing the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tradingview_scraper.symbols.stream import get_ohlcv_json, OHLCVExtractor

class TestOHLCVExtractor(unittest.TestCase):
    
    def test_single_symbol_daily(self):
        """Test fetching daily data for a single symbol."""
        print("\nTesting daily data (1D)...")
        result = get_ohlcv_json(
            symbol="BINANCE:BTCUSDT",
            timeframe="1D",
            bars_count=5,
            debug=True
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['bars_received'], 5)
        self.assertEqual(result['timeframe'], "1D")
        self.assertTrue(len(result['data']) > 0)
        
    def test_intraday_timeframe_conversion(self):
        """Test that intraday timeframes (1h) are converted and work correctly."""
        print("\nTesting intraday data (1h)...")
        # This tests the _convert_timeframe logic implicitly
        result = get_ohlcv_json(
            symbol="BINANCE:ETHUSDT",
            timeframe="1h",
            bars_count=3,
            debug=True
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['bars_received'], 3)
        self.assertEqual(result['timeframe'], "1h")

    def test_class_instantiation(self):
        """Test direct class instantiation."""
        extractor = OHLCVExtractor(debug_mode=True)
        self.assertIsInstance(extractor, OHLCVExtractor)
        # Check if ws_url is set correctly
        self.assertIn("wss://data.tradingview.com", extractor.ws_url)

if __name__ == '__main__':
    unittest.main()
