import os
import sys
import time
import pytest
from unittest import mock

# Add the current working directory to the system path
path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.overview import Overview


class TestOverview:
    @pytest.fixture
    def overview(self):
        """Fixture to create an instance of Overview for testing."""
        return Overview(export_result=False)

    def test_validate_symbol_valid(self, overview):
        """Test validation of valid symbols."""
        assert overview._validate_symbol('NASDAQ:AAPL') == 'NASDAQ:AAPL'
        assert overview._validate_symbol('bitstamp:btcusd') == 'BITSTAMP:BTCUSD'
        assert overview._validate_symbol(' NYSE:TSLA ') == 'NYSE:TSLA'

    def test_validate_symbol_invalid(self, overview):
        """Test validation of invalid symbols."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            overview._validate_symbol('')

        with pytest.raises(ValueError, match="must include exchange prefix"):
            overview._validate_symbol('AAPL')

    def test_field_categories(self, overview):
        """Test that field categories are defined."""
        assert len(overview.BASIC_FIELDS) > 0
        assert len(overview.PRICE_FIELDS) > 0
        assert len(overview.MARKET_FIELDS) > 0
        assert len(overview.VALUATION_FIELDS) > 0
        assert len(overview.DIVIDEND_FIELDS) > 0
        assert len(overview.FINANCIAL_FIELDS) > 0
        assert len(overview.PERFORMANCE_FIELDS) > 0
        assert len(overview.VOLATILITY_FIELDS) > 0
        assert len(overview.TECHNICAL_FIELDS) > 0

        # Check ALL_FIELDS is combination
        total_fields = (
            len(overview.BASIC_FIELDS) +
            len(overview.PRICE_FIELDS) +
            len(overview.MARKET_FIELDS) +
            len(overview.VALUATION_FIELDS) +
            len(overview.DIVIDEND_FIELDS) +
            len(overview.FINANCIAL_FIELDS) +
            len(overview.PERFORMANCE_FIELDS) +
            len(overview.VOLATILITY_FIELDS) +
            len(overview.TECHNICAL_FIELDS)
        )
        assert len(overview.ALL_FIELDS) == total_fields

    @mock.patch('tradingview_scraper.symbols.overview.requests.get')
    def test_get_symbol_overview_success(self, mock_get, overview):
        """Test successful retrieval of symbol overview."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'AAPL',
            'description': 'Apple Inc.',
            'close': 150.25,
            'market_cap_basic': 2500000000000,
            'change': 2.5
        }
        mock_get.return_value = mock_response

        # Get overview
        time.sleep(3)
        result = overview.get_symbol_overview(symbol='NASDAQ:AAPL')

        # Assertions
        assert result['status'] == 'success'
        assert 'data' in result
        assert result['data']['name'] == 'AAPL'
        assert result['data']['symbol'] == 'NASDAQ:AAPL'

    @mock.patch('tradingview_scraper.symbols.overview.requests.get')
    def test_get_symbol_overview_no_data(self, mock_get, overview):
        """Test getting overview with no data."""
        # Mock response with empty data
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        # Get overview
        time.sleep(3)
        result = overview.get_symbol_overview(symbol='NASDAQ:INVALID')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    @mock.patch('tradingview_scraper.symbols.overview.requests.get')
    def test_get_symbol_overview_http_error(self, mock_get, overview):
        """Test getting overview with HTTP error."""
        # Mock error response
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        # Get overview
        time.sleep(3)
        result = overview.get_symbol_overview(symbol='NASDAQ:AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    @mock.patch('tradingview_scraper.symbols.overview.requests.get')
    def test_get_symbol_overview_request_exception(self, mock_get, overview):
        """Test getting overview with request exception."""
        # Mock exception
        mock_get.side_effect = Exception('Connection error')

        # Get overview
        time.sleep(3)
        result = overview.get_symbol_overview(symbol='NASDAQ:AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    def test_get_symbol_overview_real_aapl(self, overview):
        """Test getting real overview for AAPL."""
        time.sleep(3)
        result = overview.get_symbol_overview(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        assert data['symbol'] == 'NASDAQ:AAPL'
        assert data['name'] == 'AAPL'
        assert 'close' in data
        assert 'market_cap_basic' in data
        assert 'description' in data

    def test_get_symbol_overview_real_btcusd(self, overview):
        """Test getting real overview for BTCUSD."""
        time.sleep(3)
        result = overview.get_symbol_overview(symbol='BITSTAMP:BTCUSD')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        assert data['symbol'] == 'BITSTAMP:BTCUSD'
        assert 'close' in data
        assert 'volume' in data

    def test_get_symbol_overview_with_custom_fields(self, overview):
        """Test getting overview with custom fields."""
        time.sleep(3)
        custom_fields = ['name', 'close', 'volume', 'market_cap_basic', 'change']

        result = overview.get_symbol_overview(
            symbol='NASDAQ:AAPL',
            fields=custom_fields
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        assert 'name' in data
        assert 'close' in data
        assert 'volume' in data

    def test_get_profile(self, overview):
        """Test getting profile data."""
        time.sleep(3)
        result = overview.get_profile(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        assert 'name' in data
        assert 'description' in data
        assert 'exchange' in data
        assert 'sector' in data

    def test_get_statistics(self, overview):
        """Test getting statistics data."""
        time.sleep(3)
        result = overview.get_statistics(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        assert 'market_cap_basic' in data or 'market_cap_calc' in data
        assert 'price_earnings_ttm' in data

    def test_get_financials(self, overview):
        """Test getting financial data."""
        time.sleep(3)
        result = overview.get_financials(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        assert 'total_revenue' in data or 'net_income_fy' in data

    def test_get_performance(self, overview):
        """Test getting performance data."""
        time.sleep(3)
        result = overview.get_performance(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        assert 'Perf.W' in data
        assert 'Perf.1M' in data
        assert 'Perf.Y' in data

    def test_get_technicals(self, overview):
        """Test getting technical data."""
        time.sleep(3)
        result = overview.get_technicals(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        assert 'RSI' in data
        assert 'Recommend.All' in data
        assert 'Volatility.D' in data

    def test_invalid_symbol_format(self, overview):
        """Test getting overview with invalid symbol format."""
        result = overview.get_symbol_overview(symbol='AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'must include exchange prefix' in result['error']

    def test_empty_symbol(self, overview):
        """Test getting overview with empty symbol."""
        result = overview.get_symbol_overview(symbol='')

        # Assertions
        assert result['status'] == 'failed'
        assert 'must be a non-empty string' in result['error']
