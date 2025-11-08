"""Test script for websocket realtime data generator"""

import os
import sys
import time
import unittest
from unittest import mock

PATH = str(os.getcwd())
if PATH not in sys.path:
    sys.path.append(PATH)
    
from tradingview_scraper.symbols.stream.price import RealTimeData


class TestRealTimeData(unittest.TestCase):

    @mock.patch.object(RealTimeData, 'get_latest_trade_info')
    def test_returns_generator(self, mock_get_latest_trade_info):
        """Test that the method returns a generator."""
        # Create a mock generator
        mock_generator = ({"m": "mock_data"} for _ in range(10))
        mock_get_latest_trade_info.return_value = mock_generator

        # Instantiate the RealTimeData class
        real_time_data = RealTimeData()
        exchange_symbol = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "FXOPEN:XAUUSD"]
        
        # Get the generator
        time.sleep(3)
        data_generator = real_time_data.get_latest_trade_info(exchange_symbol=exchange_symbol)

        # Check that the returned object is a generator
        self.assertTrue(hasattr(data_generator, '__iter__'))

    @mock.patch.object(RealTimeData, 'get_latest_trade_info')
    def test_generator_yields_valid_data(self, mock_get_latest_trade_info):
        """Test that the generator yields valid data."""
        # Create a mock generator with initialization packets followed by valid data
        mock_generator = ({"m": "mock_data"} if i > 0 else {"init": "initialization_data"} for i in range(10))
        mock_get_latest_trade_info.return_value = mock_generator

        # Instantiate the RealTimeData class
        real_time_data = RealTimeData()
        exchange_symbol = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "FXOPEN:XAUUSD"]
        
        # Get the generator
        time.sleep(3)
        data_generator = real_time_data.get_latest_trade_info(exchange_symbol=exchange_symbol)

        # Loop through the generator for 10 iterations
        for i, packet in enumerate(data_generator):
            print('-' * 50)
            print(packet)

            # Check if the packet exists and has the field "m" after initialization
            if i > 0:  # Skip the first packet which is an initialization packet
                self.assertIn("m", packet)
            else:
                self.assertNotIn("m", packet)  # First packet should not have "m"

if __name__ == "__main__":
    unittest.main()
