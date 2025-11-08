import os
import sys
import time
import pytest
from datetime import datetime, timedelta
from unittest import mock

# Add the current working directory to the system path
path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.cal import CalendarScraper


class TestCalendar:
    @pytest.fixture
    def calendar_scraper(self):
        """Fixture to create an instance of CalendarScraper for testing."""
        return CalendarScraper(export_result=False)

    def test_scrape_earnings_all_markets(self, calendar_scraper):
        """Test scraping earnings from all markets."""
        time.sleep(3)

        # Scrape earnings from all markets
        result = calendar_scraper.scrape_earnings(
            values=["logoid", "name", "earnings_per_share_fq"]
        )

        # Assertions
        assert result is not None
        assert isinstance(result, dict) or isinstance(result, list)

        # If it returns a dict with status
        if isinstance(result, dict):
            assert 'status' in result or len(result) > 0

    def test_scrape_earnings_specific_market(self, calendar_scraper):
        """Test scraping earnings from specific market (America)."""
        time.sleep(3)

        # Get timestamps for next 7 days
        timestamp_now = datetime.now().timestamp()
        timestamp_in_7_days = (datetime.now() + timedelta(days=7)).timestamp()

        # Scrape earnings from American market
        result = calendar_scraper.scrape_earnings(
            timestamp_now,
            timestamp_in_7_days,
            ["america"],
            values=["logoid", "name", "earnings_per_share_fq"]
        )

        # Assertions
        assert result is not None
        assert isinstance(result, dict) or isinstance(result, list)

    def test_scrape_earnings_with_custom_fields(self, calendar_scraper):
        """Test scraping earnings with custom fields."""
        time.sleep(3)

        # Scrape earnings with specific fields
        result = calendar_scraper.scrape_earnings(
            values=["logoid", "name", "earnings_per_share_fq", "market_cap_basic"]
        )

        # Assertions
        assert result is not None

    def test_scrape_dividends_all_markets(self, calendar_scraper):
        """Test scraping dividends from all markets."""
        time.sleep(3)

        # Scrape dividends from all markets
        result = calendar_scraper.scrape_dividends(
            values=["logoid", "name", "dividends_yield"]
        )

        # Assertions
        assert result is not None
        assert isinstance(result, dict) or isinstance(result, list)

        # If it returns a dict with status
        if isinstance(result, dict):
            assert 'status' in result or len(result) > 0

    def test_scrape_dividends_specific_market(self, calendar_scraper):
        """Test scraping dividends from specific market (America)."""
        time.sleep(3)

        # Get timestamps for next 7 days
        timestamp_now = datetime.now().timestamp()
        timestamp_in_7_days = (datetime.now() + timedelta(days=7)).timestamp()

        # Scrape dividends from American market
        result = calendar_scraper.scrape_dividends(
            timestamp_now,
            timestamp_in_7_days,
            ["america"],
            values=["logoid", "name", "dividends_yield"]
        )

        # Assertions
        assert result is not None
        assert isinstance(result, dict) or isinstance(result, list)

    def test_scrape_dividends_with_custom_fields(self, calendar_scraper):
        """Test scraping dividends with custom fields."""
        time.sleep(3)

        # Scrape dividends with specific fields
        result = calendar_scraper.scrape_dividends(
            values=["logoid", "name", "dividends_yield"]
        )

        # Assertions
        assert result is not None

    def test_scrape_earnings_date_range(self, calendar_scraper):
        """Test scraping earnings within a specific date range."""
        time.sleep(3)

        # Get timestamps for past 30 days
        timestamp_30_days_ago = (datetime.now() - timedelta(days=30)).timestamp()
        timestamp_now = datetime.now().timestamp()

        # Scrape earnings in date range
        result = calendar_scraper.scrape_earnings(
            timestamp_30_days_ago,
            timestamp_now,
            values=["logoid", "name"]
        )

        # Assertions
        assert result is not None

    @mock.patch('tradingview_scraper.symbols.cal.requests.post')
    def test_scrape_earnings_no_data(self, mock_post, calendar_scraper):
        """Test handling of no earnings data."""
        # Mock response for no data
        mock_response = mock.Mock()
        mock_response.json.return_value = {'data': []}
        mock_post.return_value = mock_response

        time.sleep(3)
        result = calendar_scraper.scrape_earnings(
            values=["logoid"]
        )

        # Check that result is returned
        assert result is not None

    def test_scrape_dividends_multiple_markets(self, calendar_scraper):
        """Test scraping dividends from multiple markets."""
        time.sleep(3)

        # Get timestamps for next 30 days
        timestamp_now = datetime.now().timestamp()
        timestamp_in_30_days = (datetime.now() + timedelta(days=30)).timestamp()

        # Scrape dividends from multiple markets
        result = calendar_scraper.scrape_dividends(
            timestamp_now,
            timestamp_in_30_days,
            ["america", "uk"],
            values=["logoid", "name", "dividends_yield"]
        )

        # Assertions
        assert result is not None
