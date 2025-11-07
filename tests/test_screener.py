import os
import sys
import time
import pytest
from unittest import mock

# Add the current working directory to the system path
path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.screener import Screener


class TestScreener:
    @pytest.fixture
    def screener(self):
        """Fixture to create an instance of Screener for testing."""
        return Screener(export_result=False)

    def test_validate_market_valid(self, screener):
        """Test validation of valid markets."""
        try:
            screener._validate_market('america')
            screener._validate_market('crypto')
            screener._validate_market('forex')
        except ValueError:
            pytest.fail("Valid market should not raise ValueError")

    def test_validate_market_invalid(self, screener):
        """Test validation of invalid market."""
        with pytest.raises(ValueError, match="Unsupported market"):
            screener._validate_market('invalid-market')

    def test_get_default_columns_stock(self, screener):
        """Test getting default columns for stock market."""
        columns = screener._get_default_columns('america')
        assert 'name' in columns
        assert 'close' in columns
        assert 'volume' in columns
        assert 'market_cap_basic' in columns

    def test_get_default_columns_crypto(self, screener):
        """Test getting default columns for crypto market."""
        columns = screener._get_default_columns('crypto')
        assert 'name' in columns
        assert 'close' in columns
        assert 'market_cap_calc' in columns

    def test_get_default_columns_forex(self, screener):
        """Test getting default columns for forex market."""
        columns = screener._get_default_columns('forex')
        assert 'name' in columns
        assert 'close' in columns
        assert 'Recommend.All' in columns

    def test_build_payload_basic(self, screener):
        """Test building basic payload."""
        payload = screener._build_payload(market='america')

        assert 'columns' in payload
        assert 'options' in payload
        assert 'range' in payload
        assert payload['range'] == [0, 50]

    def test_build_payload_with_filters(self, screener):
        """Test building payload with filters."""
        filters = [
            {'left': 'close', 'operation': 'greater', 'right': 100}
        ]
        payload = screener._build_payload(filters=filters, market='america')

        assert 'filter' in payload
        assert len(payload['filter']) == 1
        assert payload['filter'][0]['left'] == 'close'

    def test_build_payload_with_sort(self, screener):
        """Test building payload with sort."""
        sort = {'sortBy': 'volume', 'sortOrder': 'desc'}
        payload = screener._build_payload(sort=sort, market='america')

        assert 'sort' in payload
        assert payload['sort']['sortBy'] == 'volume'
        assert payload['sort']['sortOrder'] == 'desc'

    def test_build_payload_with_custom_columns(self, screener):
        """Test building payload with custom columns."""
        custom_columns = ['name', 'close', 'volume']
        payload = screener._build_payload(columns=custom_columns, market='america')

        assert payload['columns'] == custom_columns

    @mock.patch('tradingview_scraper.symbols.screener.requests.post')
    def test_screen_success(self, mock_post, screener):
        """Test successful screening."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    's': 'NASDAQ:AAPL',
                    'd': ['Apple Inc.', 150.25, 2.5, 3.75, 50000000, 0.8, 2500000000000, 25.5, 6.0]
                },
                {
                    's': 'NASDAQ:GOOGL',
                    'd': ['Alphabet Inc.', 2800.00, 1.8, 50.00, 30000000, 0.7, 1800000000000, 28.0, 100.0]
                }
            ],
            'totalCount': 2
        }
        mock_post.return_value = mock_response

        # Screen data
        time.sleep(3)
        result = screener.screen(market='america', limit=10)

        # Assertions
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']) == 2
        assert result['data'][0]['symbol'] == 'NASDAQ:AAPL'

    @mock.patch('tradingview_scraper.symbols.screener.requests.post')
    def test_screen_with_filters(self, mock_post, screener):
        """Test screening with filters."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    's': 'NASDAQ:AAPL',
                    'd': ['Apple Inc.', 150.25, 2.5, 3.75, 50000000]
                }
            ],
            'totalCount': 1
        }
        mock_post.return_value = mock_response

        # Screen with filters
        time.sleep(3)
        filters = [
            {'left': 'close', 'operation': 'greater', 'right': 100}
        ]
        result = screener.screen(market='america', filters=filters, limit=10)

        # Assertions
        assert result['status'] == 'success'
        assert len(result['data']) == 1

    @mock.patch('tradingview_scraper.symbols.screener.requests.post')
    def test_screen_http_error(self, mock_post, screener):
        """Test screening with HTTP error."""
        # Mock error response
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        # Screen data
        time.sleep(3)
        result = screener.screen(market='america')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    @mock.patch('tradingview_scraper.symbols.screener.requests.post')
    def test_screen_request_exception(self, mock_post, screener):
        """Test screening with request exception."""
        # Mock exception
        mock_post.side_effect = Exception('Connection error')

        # Screen data
        time.sleep(3)
        result = screener.screen(market='america')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    def test_screen_real_america(self, screener):
        """Test screening real US stocks."""
        time.sleep(3)
        filters = [
            {'left': 'close', 'operation': 'greater', 'right': 10},
            {'left': 'volume', 'operation': 'greater', 'right': 100000}
        ]
        result = screener.screen(
            market='america',
            filters=filters,
            sort_by='volume',
            sort_order='desc',
            limit=5
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']) >= 1

    def test_screen_real_crypto(self, screener):
        """Test screening real crypto."""
        time.sleep(3)
        result = screener.screen(
            market='crypto',
            sort_by='volume',
            limit=5
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']) >= 1

    def test_screen_real_forex(self, screener):
        """Test screening real forex pairs."""
        time.sleep(3)
        result = screener.screen(
            market='forex',
            limit=5
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_screen_with_custom_columns(self, screener):
        """Test screening with custom columns."""
        time.sleep(3)
        custom_columns = ['name', 'close', 'volume']
        result = screener.screen(
            market='america',
            columns=custom_columns,
            limit=3
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        if len(result['data']) > 0:
            assert 'name' in result['data'][0]
            assert 'close' in result['data'][0]
            assert 'volume' in result['data'][0]

    def test_screen_with_range_filter(self, screener):
        """Test screening with range filter."""
        time.sleep(3)
        filters = [
            {'left': 'close', 'operation': 'in_range', 'right': [50, 200]}
        ]
        result = screener.screen(
            market='america',
            filters=filters,
            limit=5
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
