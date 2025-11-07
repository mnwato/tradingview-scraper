import os
import sys
import time
import pytest
from unittest import mock

# Add the current working directory to the system path
path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.market_movers import MarketMovers


class TestMarketMovers:
    @pytest.fixture
    def market_movers_scraper(self):
        """Fixture to create an instance of MarketMovers for testing."""
        return MarketMovers(export_result=False)

    def test_validate_market_valid(self, market_movers_scraper):
        """Test validation of valid markets."""
        try:
            market_movers_scraper._validate_market('stocks-usa')
            market_movers_scraper._validate_market('crypto')
            market_movers_scraper._validate_market('forex')
        except ValueError:
            pytest.fail("Valid market should not raise ValueError")

    def test_validate_market_invalid(self, market_movers_scraper):
        """Test validation of invalid market."""
        with pytest.raises(ValueError, match="Unsupported market"):
            market_movers_scraper._validate_market('invalid-market')

    def test_validate_category_valid(self, market_movers_scraper):
        """Test validation of valid categories."""
        try:
            market_movers_scraper._validate_category('gainers', 'stocks-usa')
            market_movers_scraper._validate_category('losers', 'stocks-usa')
            market_movers_scraper._validate_category('penny-stocks', 'stocks-usa')
        except ValueError:
            pytest.fail("Valid category should not raise ValueError")

    def test_validate_category_invalid(self, market_movers_scraper):
        """Test validation of invalid category."""
        with pytest.raises(ValueError, match="Unsupported category"):
            market_movers_scraper._validate_category('invalid-category', 'stocks-usa')

    def test_get_scanner_url(self, market_movers_scraper):
        """Test getting correct scanner URLs for different markets."""
        assert market_movers_scraper._get_scanner_url('stocks-usa') == "https://scanner.tradingview.com/america/scan"
        assert market_movers_scraper._get_scanner_url('crypto') == "https://scanner.tradingview.com/crypto/scan"
        assert market_movers_scraper._get_scanner_url('forex') == "https://scanner.tradingview.com/forex/scan"

    def test_build_scanner_payload(self, market_movers_scraper):
        """Test building scanner payload."""
        payload = market_movers_scraper._build_scanner_payload(
            market='stocks-usa',
            category='gainers',
            limit=10
        )

        assert 'columns' in payload
        assert 'filter' in payload
        assert 'range' in payload
        assert payload['range'] == [0, 10]
        assert 'sort' in payload

    def test_get_filter_conditions_gainers(self, market_movers_scraper):
        """Test filter conditions for gainers."""
        filters = market_movers_scraper._get_filter_conditions('stocks-usa', 'gainers')

        # Should have market filter and change > 0 filter
        assert len(filters) >= 2
        assert any(f.get('left') == 'change' and f.get('operation') == 'greater' for f in filters)

    def test_get_filter_conditions_penny_stocks(self, market_movers_scraper):
        """Test filter conditions for penny stocks."""
        filters = market_movers_scraper._get_filter_conditions('stocks-usa', 'penny-stocks')

        # Should have market filter and price < 5 filter
        assert len(filters) >= 2
        assert any(f.get('left') == 'close' and f.get('operation') == 'less' for f in filters)

    def test_get_sort_config_gainers(self, market_movers_scraper):
        """Test sort configuration for gainers."""
        sort_config = market_movers_scraper._get_sort_config('gainers')

        assert sort_config['sortBy'] == 'change'
        assert sort_config['sortOrder'] == 'desc'

    def test_get_sort_config_losers(self, market_movers_scraper):
        """Test sort configuration for losers."""
        sort_config = market_movers_scraper._get_sort_config('losers')

        assert sort_config['sortBy'] == 'change'
        assert sort_config['sortOrder'] == 'asc'

    def test_get_sort_config_most_active(self, market_movers_scraper):
        """Test sort configuration for most active."""
        sort_config = market_movers_scraper._get_sort_config('most-active')

        assert sort_config['sortBy'] == 'volume'
        assert sort_config['sortOrder'] == 'desc'

    @mock.patch('tradingview_scraper.symbols.market_movers.requests.post')
    def test_scrape_success(self, mock_post, market_movers_scraper):
        """Test successful scraping of market movers."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    's': 'NASDAQ:AAPL',
                    'd': ['Apple Inc.', 150.25, 2.5, 3.75, 50000000, 2500000000000, 25.5, 6.0, 'logo-id', 'Tech company']
                },
                {
                    's': 'NASDAQ:GOOGL',
                    'd': ['Alphabet Inc.', 2800.00, 1.8, 50.00, 30000000, 1800000000000, 28.0, 100.0, 'logo-id-2', 'Tech company']
                }
            ]
        }
        mock_post.return_value = mock_response

        # Scrape data
        time.sleep(3)
        result = market_movers_scraper.scrape(market='stocks-usa', category='gainers', limit=10)

        # Assertions
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']) == 2
        assert result['data'][0]['symbol'] == 'NASDAQ:AAPL'

    @mock.patch('tradingview_scraper.symbols.market_movers.requests.post')
    def test_scrape_http_error(self, mock_post, market_movers_scraper):
        """Test scraping with HTTP error."""
        # Mock error response
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        # Scrape data
        time.sleep(3)
        result = market_movers_scraper.scrape(market='stocks-usa', category='gainers')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    @mock.patch('tradingview_scraper.symbols.market_movers.requests.post')
    def test_scrape_request_exception(self, mock_post, market_movers_scraper):
        """Test scraping with request exception."""
        # Mock exception
        mock_post.side_effect = Exception('Connection error')

        # Scrape data
        time.sleep(3)
        result = market_movers_scraper.scrape(market='stocks-usa', category='gainers')

        # Assertions
        assert result['status'] == 'failed'
        assert 'error' in result

    def test_scrape_real_gainers(self, market_movers_scraper):
        """Test scraping real gainers data."""
        time.sleep(3)
        result = market_movers_scraper.scrape(
            market='stocks-usa',
            category='gainers',
            limit=5
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']) >= 1

    def test_scrape_real_losers(self, market_movers_scraper):
        """Test scraping real losers data."""
        time.sleep(3)
        result = market_movers_scraper.scrape(
            market='stocks-usa',
            category='losers',
            limit=5
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result
        assert len(result['data']) >= 1

    def test_scrape_real_penny_stocks(self, market_movers_scraper):
        """Test scraping real penny stocks data."""
        time.sleep(3)
        result = market_movers_scraper.scrape(
            market='stocks-usa',
            category='penny-stocks',
            limit=5
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        assert 'data' in result

    def test_scrape_with_custom_fields(self, market_movers_scraper):
        """Test scraping with custom fields."""
        time.sleep(3)
        custom_fields = ['name', 'close', 'change', 'volume']
        result = market_movers_scraper.scrape(
            market='stocks-usa',
            category='gainers',
            fields=custom_fields,
            limit=5
        )

        # Assertions
        assert result is not None
        assert result['status'] == 'success'
        if len(result['data']) > 0:
            assert 'name' in result['data'][0]
            assert 'close' in result['data'][0]
