import os
import sys
import time
import pytest
from unittest import mock

# Add the current working directory to the system path
path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.symbol_markets import SymbolMarkets


class TestSymbolMarkets:
    @pytest.fixture
    def symbol_markets(self):
        """Fixture to create an instance of SymbolMarkets for testing."""
        return SymbolMarkets(export_result=False)

    def test_build_payload_basic(self, symbol_markets):
        """Test building basic payload."""
        payload = symbol_markets._build_payload(symbol='AAPL')

        assert 'filter' in payload
        assert 'columns' in payload
        assert 'range' in payload
        assert payload['range'] == [0, 150]
        assert payload['filter'][0]['left'] == 'name'
        assert payload['filter'][0]['operation'] == 'match'
        assert payload['filter'][0]['right'] == 'AAPL'

    def test_build_payload_with_custom_columns(self, symbol_markets):
        """Test building payload with custom columns."""
        custom_columns = ['name', 'close', 'volume', 'exchange']
        payload = symbol_markets._build_payload(
            symbol='BTCUSD',
            columns=custom_columns
        )

        assert payload['columns'] == custom_columns

    def test_build_payload_with_limit(self, symbol_markets):
        """Test building payload with custom limit."""
        payload = symbol_markets._build_payload(
            symbol='TSLA',
            limit=50
        )

        assert payload['range'] == [0, 50]

    @mock.patch('tradingview_scraper.symbols.symbol_markets.requests.post')
    def test_scrape_success(self, mock_post, symbol_markets):
        """Test successful scraping."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    's': 'NASDAQ:AAPL',
                    'd': ['AAPL', 150.25, 2.5, 3.75, 50000000, 'NASDAQ', 'stock', 'Apple Inc.', 'USD', 2500000000000]
                },
                {
                    's': 'GPW:AAPL',
                    'd': ['AAPL', 148.50, 1.2, 1.80, 1000000, 'GPW', 'stock', 'Apple Inc.', 'PLN', 2500000000000]
                }
            ],
            'totalCount': 2
        }
        mock_post.return_value = mock_response

        # Scrape data
        time.sleep(3)
        result = symbol_markets.scrape(symbol='AAPL')

        # Assertions
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']) == 2
        assert result['data'][0]['symbol'] == 'NASDAQ:AAPL'
        assert result['data'][1]['symbol'] == 'GPW:AAPL'

    @mock.patch('tradingview_scraper.symbols.symbol_markets.requests.post')
    def test_scrape_no_results(self, mock_post, symbol_markets):
        """Test scraping with no results."""
        # Mock response with no data
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [],
            'totalCount': 0
        }
        mock_post.return_value = mock_response

        # Scrape data
        time.sleep(3)
        result = symbol_markets.scrape(symbol='INVALID')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result
        assert 'No markets found' in result['error']

    @mock.patch('tradingview_scraper.symbols.symbol_markets.requests.post')
    def test_scrape_http_error(self, mock_post, symbol_markets):
        """Test scraping with HTTP error."""
        # Mock error response
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        # Scrape data
        time.sleep(3)
        result = symbol_markets.scrape(symbol='AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    @mock.patch('tradingview_scraper.symbols.symbol_markets.requests.post')
    def test_scrape_request_exception(self, mock_post, symbol_markets):
        """Test scraping with request exception."""
        # Mock exception
        mock_post.side_effect = Exception('Connection error')

        # Scrape data
        time.sleep(3)
        result = symbol_markets.scrape(symbol='AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    def test_scrape_invalid_scanner(self, symbol_markets):
        """Test scraping with invalid scanner."""
        result = symbol_markets.scrape(symbol='AAPL', scanner='invalid-scanner')

        # Assertions
        assert result['status'] == 'failed'
        assert 'Unsupported scanner' in result['error']

    def test_scrape_real_aapl_global(self, symbol_markets):
        """Test scraping real AAPL markets globally."""
        time.sleep(3)
        result = symbol_markets.scrape(symbol='AAPL', scanner='global', limit=100)

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
        assert result['total'] >= 1

        # Check that NASDAQ:AAPL is in the results
        symbols = [item['symbol'] for item in result['data']]
        assert 'NASDAQ:AAPL' in symbols

    def test_scrape_real_aapl_america(self, symbol_markets):
        """Test scraping real AAPL markets in America."""
        time.sleep(3)
        result = symbol_markets.scrape(symbol='AAPL', scanner='america', limit=50)

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
        assert result['total'] >= 1

        # Check that data has the expected fields
        if len(result['data']) > 0:
            first_item = result['data'][0]
            assert 'symbol' in first_item
            assert 'name' in first_item
            assert 'exchange' in first_item

    def test_scrape_real_btcusd_crypto(self, symbol_markets):
        """Test scraping real BTCUSD markets in crypto."""
        time.sleep(3)
        result = symbol_markets.scrape(symbol='BTCUSD', scanner='crypto', limit=50)

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_scrape_with_custom_columns(self, symbol_markets):
        """Test scraping with custom columns."""
        time.sleep(3)
        custom_columns = ['name', 'close', 'volume', 'exchange']
        result = symbol_markets.scrape(
            symbol='AAPL',
            columns=custom_columns,
            scanner='america',
            limit=10
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        if len(result['data']) > 0:
            first_item = result['data'][0]
            assert 'name' in first_item
            assert 'close' in first_item
            assert 'volume' in first_item
            assert 'exchange' in first_item

    def test_supported_scanners(self, symbol_markets):
        """Test that all supported scanners are accessible."""
        supported_scanners = ['global', 'america', 'crypto', 'forex', 'cfd']

        for scanner in supported_scanners:
            assert scanner in symbol_markets.SCANNER_ENDPOINTS
            assert symbol_markets.SCANNER_ENDPOINTS[scanner].startswith('https://')

    def test_default_columns(self, symbol_markets):
        """Test that default columns are defined."""
        assert len(symbol_markets.DEFAULT_COLUMNS) > 0
        assert 'name' in symbol_markets.DEFAULT_COLUMNS
        assert 'close' in symbol_markets.DEFAULT_COLUMNS
        assert 'exchange' in symbol_markets.DEFAULT_COLUMNS
