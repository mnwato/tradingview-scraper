import os
import sys
import time
import pytest
from unittest import mock

# Add the current working directory to the system path
path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.minds import Minds


class TestMinds:
    @pytest.fixture
    def minds(self):
        """Fixture to create an instance of Minds for testing."""
        return Minds(export_result=False)

    def test_validate_symbol_valid(self, minds):
        """Test validation of valid symbols."""
        assert minds._validate_symbol('NASDAQ:AAPL') == 'NASDAQ:AAPL'
        assert minds._validate_symbol('bitstamp:btcusd') == 'BITSTAMP:BTCUSD'
        assert minds._validate_symbol(' NYSE:TSLA ') == 'NYSE:TSLA'

    def test_validate_symbol_invalid(self, minds):
        """Test validation of invalid symbols."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            minds._validate_symbol('')

        with pytest.raises(ValueError, match="must include exchange prefix"):
            minds._validate_symbol('AAPL')

    def test_validate_sort_valid(self, minds):
        """Test validation of valid sort options."""
        assert minds._validate_sort('recent') == 'recent'
        assert minds._validate_sort('popular') == 'popular'
        assert minds._validate_sort('trending') == 'trending'

    def test_validate_sort_invalid(self, minds):
        """Test validation of invalid sort options."""
        with pytest.raises(ValueError, match="Unsupported sort option"):
            minds._validate_sort('invalid')

    def test_sort_options(self, minds):
        """Test that sort options are defined."""
        assert len(minds.SORT_OPTIONS) > 0
        assert 'recent' in minds.SORT_OPTIONS
        assert 'popular' in minds.SORT_OPTIONS
        assert 'trending' in minds.SORT_OPTIONS

    @mock.patch('tradingview_scraper.symbols.minds.requests.get')
    def test_get_minds_success(self, mock_get, minds):
        """Test successful retrieval of minds."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'text': 'Test discussion about AAPL',
                    'symbols': {'AAPL': 'NASDAQ:AAPL'},
                    'uid': 'test123',
                    'url': 'https://www.tradingview.com/minds/test',
                    'author': {
                        'username': 'testuser',
                        'uri': '/u/testuser/',
                        'is_broker': False
                    },
                    'created': '2025-01-07T12:00:00+00:00',
                    'total_likes': 10,
                    'total_comments': 5,
                    'modified': False,
                    'hidden': False
                }
            ],
            'next': '/api/v1/minds/?c=test&symbol=NASDAQ:AAPL',
            'meta': {
                'symbol': 'NASDAQ:AAPL',
                'symbols_info': {
                    'NASDAQ:AAPL': {
                        'short_name': 'AAPL',
                        'exchange': 'NASDAQ'
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        # Get minds
        time.sleep(3)
        result = minds.get_minds(symbol='NASDAQ:AAPL', limit=10)

        # Assertions
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']) == 1
        assert result['data'][0]['text'] == 'Test discussion about AAPL'
        assert result['data'][0]['author']['username'] == 'testuser'

    @mock.patch('tradingview_scraper.symbols.minds.requests.get')
    def test_get_minds_no_data(self, mock_get, minds):
        """Test getting minds with no data."""
        # Mock response with empty results
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [],
            'meta': {}
        }
        mock_get.return_value = mock_response

        # Get minds
        time.sleep(3)
        result = minds.get_minds(symbol='NASDAQ:INVALID')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    @mock.patch('tradingview_scraper.symbols.minds.requests.get')
    def test_get_minds_http_error(self, mock_get, minds):
        """Test getting minds with HTTP error."""
        # Mock error response
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        # Get minds
        time.sleep(3)
        result = minds.get_minds(symbol='NASDAQ:AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    @mock.patch('tradingview_scraper.symbols.minds.requests.get')
    def test_get_minds_request_exception(self, mock_get, minds):
        """Test getting minds with request exception."""
        # Mock exception
        mock_get.side_effect = Exception('Connection error')

        # Get minds
        time.sleep(3)
        result = minds.get_minds(symbol='NASDAQ:AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    def test_get_minds_real_aapl_recent(self, minds):
        """Test getting real minds for AAPL with recent sort."""
        time.sleep(3)
        result = minds.get_minds(
            symbol='NASDAQ:AAPL',
            sort='recent',
            limit=10
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']) >= 1

        # Check structure of first item
        if len(result['data']) > 0:
            first = result['data'][0]
            assert 'text' in first
            assert 'author' in first
            assert 'username' in first['author']
            assert 'total_likes' in first
            assert 'total_comments' in first

    def test_get_minds_real_aapl_popular(self, minds):
        """Test getting real minds for AAPL with popular sort."""
        time.sleep(3)
        result = minds.get_minds(
            symbol='NASDAQ:AAPL',
            sort='popular',
            limit=10
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_minds_real_btcusd(self, minds):
        """Test getting real minds for BTCUSD."""
        time.sleep(3)
        result = minds.get_minds(
            symbol='BITSTAMP:BTCUSD',
            sort='recent',
            limit=10
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_get_minds_with_symbol_info(self, minds):
        """Test that symbol info is included in response."""
        time.sleep(3)
        result = minds.get_minds(
            symbol='NASDAQ:AAPL',
            sort='recent',
            limit=5
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'symbol_info' in result

    def test_get_minds_pagination(self, minds):
        """Test that pagination cursor is returned."""
        time.sleep(3)
        result = minds.get_minds(
            symbol='NASDAQ:AAPL',
            sort='recent',
            limit=10
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'next_cursor' in result

    def test_invalid_symbol_format(self, minds):
        """Test getting minds with invalid symbol format."""
        result = minds.get_minds(symbol='AAPL')

        # Assertions
        assert result['status'] == 'failed'
        assert 'must include exchange prefix' in result['error']

    def test_empty_symbol(self, minds):
        """Test getting minds with empty symbol."""
        result = minds.get_minds(symbol='')

        # Assertions
        assert result['status'] == 'failed'
        assert 'must be a non-empty string' in result['error']

    def test_invalid_sort_option(self, minds):
        """Test getting minds with invalid sort option."""
        result = minds.get_minds(symbol='NASDAQ:AAPL', sort='invalid')

        # Assertions
        assert result['status'] == 'failed'
        assert 'Unsupported sort option' in result['error']

    def test_parse_mind(self, minds):
        """Test parsing of a mind item."""
        raw_item = {
            'text': 'Test discussion',
            'symbols': {'AAPL': 'NASDAQ:AAPL'},
            'uid': 'test123',
            'url': 'https://test.com',
            'author': {
                'username': 'testuser',
                'uri': '/u/testuser/',
                'is_broker': False
            },
            'created': '2025-01-07T12:00:00+00:00',
            'total_likes': 10,
            'total_comments': 5,
            'modified': False,
            'hidden': False
        }

        parsed = minds._parse_mind(raw_item)

        assert parsed['text'] == 'Test discussion'
        assert parsed['author']['username'] == 'testuser'
        assert parsed['total_likes'] == 10
        assert parsed['symbols'] == ['NASDAQ:AAPL']

    @mock.patch('tradingview_scraper.symbols.minds.requests.get')
    def test_get_all_minds(self, mock_get, minds):
        """Test getting all minds with pagination."""
        # Mock first page
        mock_response1 = mock.Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            'results': [
                {
                    'text': 'Discussion 1',
                    'symbols': {},
                    'uid': 'test1',
                    'url': 'url1',
                    'author': {'username': 'user1', 'uri': '/u/user1/', 'is_broker': False},
                    'created': '2025-01-07T12:00:00+00:00',
                    'total_likes': 5,
                    'total_comments': 2,
                    'modified': False,
                    'hidden': False
                }
            ],
            'next': '/api/v1/minds/?c=cursor1&symbol=NASDAQ:AAPL',
            'meta': {}
        }

        # Mock second page
        mock_response2 = mock.Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            'results': [
                {
                    'text': 'Discussion 2',
                    'symbols': {},
                    'uid': 'test2',
                    'url': 'url2',
                    'author': {'username': 'user2', 'uri': '/u/user2/', 'is_broker': False},
                    'created': '2025-01-07T13:00:00+00:00',
                    'total_likes': 3,
                    'total_comments': 1,
                    'modified': False,
                    'hidden': False
                }
            ],
            'next': '',
            'meta': {}
        }

        mock_get.side_effect = [mock_response1, mock_response2]

        time.sleep(3)
        result = minds.get_all_minds(symbol='NASDAQ:AAPL', max_results=100)

        assert result['status'] == 'success'
        assert len(result['data']) == 2
        assert result['pages'] == 2
