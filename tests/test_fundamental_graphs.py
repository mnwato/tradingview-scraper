import os
import sys
import time
import pytest
from unittest import mock

# Add the current working directory to the system path
path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.fundamental_graphs import FundamentalGraphs


class TestFundamentalGraphs:
    @pytest.fixture
    def fundamentals(self):
        """Fixture to create an instance of FundamentalGraphs for testing."""
        return FundamentalGraphs(export_result=False)

    def test_validate_symbol_valid(self, fundamentals):
        """Test validation of valid symbols."""
        assert fundamentals._validate_symbol('NASDAQ:AAPL') == 'NASDAQ:AAPL'
        assert fundamentals._validate_symbol('nyse:jpm') == 'NYSE:JPM'
        assert fundamentals._validate_symbol(' NASDAQ:MSFT ') == 'NASDAQ:MSFT'

    def test_validate_symbol_invalid(self, fundamentals):
        """Test validation of invalid symbols."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            fundamentals._validate_symbol('')

        with pytest.raises(ValueError, match="must include exchange prefix"):
            fundamentals._validate_symbol('AAPL')

    def test_field_categories(self, fundamentals):
        """Test that field categories are defined."""
        assert len(fundamentals.INCOME_STATEMENT_FIELDS) > 0
        assert len(fundamentals.BALANCE_SHEET_FIELDS) > 0
        assert len(fundamentals.CASH_FLOW_FIELDS) > 0
        assert len(fundamentals.MARGIN_FIELDS) > 0
        assert len(fundamentals.PROFITABILITY_FIELDS) > 0
        assert len(fundamentals.LIQUIDITY_FIELDS) > 0
        assert len(fundamentals.LEVERAGE_FIELDS) > 0
        assert len(fundamentals.VALUATION_FIELDS) > 0
        assert len(fundamentals.DIVIDEND_FIELDS) > 0

        # Check ALL_FIELDS is combination
        total_fields = (
            len(fundamentals.INCOME_STATEMENT_FIELDS) +
            len(fundamentals.BALANCE_SHEET_FIELDS) +
            len(fundamentals.CASH_FLOW_FIELDS) +
            len(fundamentals.MARGIN_FIELDS) +
            len(fundamentals.PROFITABILITY_FIELDS) +
            len(fundamentals.LIQUIDITY_FIELDS) +
            len(fundamentals.LEVERAGE_FIELDS) +
            len(fundamentals.VALUATION_FIELDS) +
            len(fundamentals.DIVIDEND_FIELDS)
        )
        assert len(fundamentals.ALL_FIELDS) == total_fields

    @mock.patch('tradingview_scraper.symbols.fundamental_graphs.requests.get')
    def test_get_fundamentals_success(self, mock_get, fundamentals):
        """Test successful retrieval of fundamentals."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_revenue': 394000000000,
            'net_income': 100000000000,
            'EBITDA': 130000000000,
            'market_cap_basic': 2800000000000,
            'price_earnings_ttm': 28.5
        }
        mock_get.return_value = mock_response

        # Get fundamentals
        time.sleep(3)
        result = fundamentals.get_fundamentals(symbol='NASDAQ:AAPL')

        # Assertions
        assert result['status'] == 'success'
        assert 'data' in result
        assert result['data']['symbol'] == 'NASDAQ:AAPL'
        assert result['data']['total_revenue'] == 394000000000

    @mock.patch('tradingview_scraper.symbols.fundamental_graphs.requests.get')
    def test_get_fundamentals_no_data(self, mock_get, fundamentals):
        """Test getting fundamentals with no data."""
        # Mock response with empty data
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        # Get fundamentals
        time.sleep(3)
        result = fundamentals.get_fundamentals(symbol='NASDAQ:INVALID')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    @mock.patch('tradingview_scraper.symbols.fundamental_graphs.requests.get')
    def test_get_fundamentals_http_error(self, mock_get, fundamentals):
        """Test getting fundamentals with HTTP error."""
        # Mock error response
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        # Get fundamentals
        time.sleep(3)
        result = fundamentals.get_fundamentals(symbol='NASDAQ:AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    @mock.patch('tradingview_scraper.symbols.fundamental_graphs.requests.get')
    def test_get_fundamentals_request_exception(self, mock_get, fundamentals):
        """Test getting fundamentals with request exception."""
        # Mock exception
        mock_get.side_effect = Exception('Connection error')

        # Get fundamentals
        time.sleep(3)
        result = fundamentals.get_fundamentals(symbol='NASDAQ:AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    def test_get_fundamentals_real_aapl(self, fundamentals):
        """Test getting real fundamentals for AAPL."""
        time.sleep(3)
        result = fundamentals.get_fundamentals(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        assert data['symbol'] == 'NASDAQ:AAPL'
        # Check at least some fundamental fields are present
        has_revenue = 'total_revenue' in data or 'total_revenue_fy' in data
        has_income = 'net_income' in data or 'net_income_fy' in data
        assert has_revenue or has_income

    def test_get_fundamentals_real_msft(self, fundamentals):
        """Test getting real fundamentals for MSFT."""
        time.sleep(3)
        result = fundamentals.get_fundamentals(symbol='NASDAQ:MSFT')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
        assert result['data']['symbol'] == 'NASDAQ:MSFT'

    def test_get_fundamentals_with_custom_fields(self, fundamentals):
        """Test getting fundamentals with custom fields."""
        time.sleep(3)
        custom_fields = ['total_revenue', 'net_income', 'EBITDA', 'market_cap_basic']

        result = fundamentals.get_fundamentals(
            symbol='NASDAQ:AAPL',
            fields=custom_fields
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_income_statement(self, fundamentals):
        """Test getting income statement data."""
        time.sleep(3)
        result = fundamentals.get_income_statement(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_balance_sheet(self, fundamentals):
        """Test getting balance sheet data."""
        time.sleep(3)
        result = fundamentals.get_balance_sheet(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_cash_flow(self, fundamentals):
        """Test getting cash flow data."""
        time.sleep(3)
        result = fundamentals.get_cash_flow(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_margins(self, fundamentals):
        """Test getting margin data."""
        time.sleep(3)
        result = fundamentals.get_margins(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_profitability(self, fundamentals):
        """Test getting profitability data."""
        time.sleep(3)
        result = fundamentals.get_profitability(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_liquidity(self, fundamentals):
        """Test getting liquidity data."""
        time.sleep(3)
        result = fundamentals.get_liquidity(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_leverage(self, fundamentals):
        """Test getting leverage data."""
        time.sleep(3)
        result = fundamentals.get_leverage(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_valuation(self, fundamentals):
        """Test getting valuation data."""
        time.sleep(3)
        result = fundamentals.get_valuation(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

        data = result['data']
        # Check at least some valuation fields are present
        has_market_cap = 'market_cap_basic' in data or 'market_cap_calc' in data
        assert has_market_cap

    def test_get_dividends(self, fundamentals):
        """Test getting dividend data."""
        time.sleep(3)
        result = fundamentals.get_dividends(symbol='NASDAQ:AAPL')

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    @mock.patch('tradingview_scraper.symbols.fundamental_graphs.requests.get')
    def test_compare_fundamentals(self, mock_get, fundamentals):
        """Test comparing fundamentals across multiple symbols."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_revenue': 400000000000,
            'net_income': 100000000000,
            'market_cap_basic': 2800000000000
        }
        mock_get.return_value = mock_response

        time.sleep(3)
        result = fundamentals.compare_fundamentals(
            symbols=['NASDAQ:AAPL', 'NASDAQ:MSFT'],
            fields=['total_revenue', 'net_income', 'market_cap_basic']
        )

        # Assertions
        assert result['status'] == 'success'
        assert 'data' in result
        assert 'comparison' in result
        assert len(result['data']) == 2
        assert 'total_revenue' in result['comparison']

    def test_compare_fundamentals_real(self, fundamentals):
        """Test comparing real fundamentals across symbols."""
        time.sleep(3)
        result = fundamentals.compare_fundamentals(
            symbols=['NASDAQ:AAPL', 'NASDAQ:MSFT'],
            fields=['total_revenue', 'net_income']
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
        assert 'comparison' in result
        assert len(result['data']) >= 1

    def test_invalid_symbol_format(self, fundamentals):
        """Test getting fundamentals with invalid symbol format."""
        result = fundamentals.get_fundamentals(symbol='AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'must include exchange prefix' in result['error']

    def test_empty_symbol(self, fundamentals):
        """Test getting fundamentals with empty symbol."""
        result = fundamentals.get_fundamentals(symbol='')

        # Assertions
        assert result['status'] == 'failed'
        assert 'must be a non-empty string' in result['error']
