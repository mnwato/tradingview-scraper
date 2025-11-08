import os
import sys
import time
import pytest
from unittest import mock

# Add the current working directory to the system path
path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.news import NewsScraper


class TestNews:
    @pytest.fixture
    def news_scraper(self):
        """Fixture to create an instance of NewsScraper for testing."""
        return NewsScraper(export_result=False)

    def test_scrape_headlines_by_symbol(self, news_scraper):
        """Test scraping news headlines by symbol."""
        time.sleep(3)

        # Scrape news headlines for BTCUSD on BINANCE
        headlines = news_scraper.scrape_headlines(
            symbol='BTCUSD',
            exchange='BINANCE',
            sort='latest'
        )

        # Assertions - API returns list directly, not wrapped in dict
        assert headlines is not None
        assert isinstance(headlines, list)
        assert len(headlines) > 0

        # Validate headline structure
        first_headline = headlines[0]
        assert 'id' in first_headline
        assert 'link' in first_headline or 'title' in first_headline

    def test_scrape_headlines_with_provider(self, news_scraper):
        """Test scraping news headlines with specific provider."""
        time.sleep(3)

        # Scrape news headlines from a specific provider with symbol (use valid provider)
        headlines = news_scraper.scrape_headlines(
            symbol='BTCUSD',
            exchange='BINANCE',
            provider='cointelegraph',  # Valid provider from news_providers.txt
            sort='latest'
        )

        # Assertions
        assert headlines is not None
        assert isinstance(headlines, list)

    def test_scrape_news_content(self, news_scraper):
        """Test scraping detailed news content."""
        time.sleep(3)

        # First get headlines to get a story path
        headlines = news_scraper.scrape_headlines(
            symbol='BTCUSD',
            exchange='BINANCE',
            sort='latest'
        )

        assert len(headlines) > 0

        # Get the first story path
        story_path = headlines[0].get('storyPath') or headlines[0].get('link', '').replace('https://tradingview.com', '')

        if not story_path:
            pytest.skip("No valid story path found in headlines")

        # Scrape the detailed content
        time.sleep(3)
        content = news_scraper.scrape_news_content(story_path=story_path)

        # Assertions
        assert content is not None
        assert isinstance(content, dict)

        # Validate content structure
        assert 'title' in content or 'breadcrumbs' in content

    @mock.patch('tradingview_scraper.symbols.news.requests.get')
    def test_scrape_headlines_no_data(self, mock_get, news_scraper):
        """Test handling of no news found."""
        # Mock response for no news
        mock_response = mock.Mock()
        mock_response.json.return_value = {'items': []}
        mock_get.return_value = mock_response

        time.sleep(3)
        headlines = news_scraper.scrape_headlines(
            symbol='BTCUSD',
            exchange='BINANCE'
        )

        # Check that empty list is returned
        assert headlines is not None
        assert isinstance(headlines, list)
        assert len(headlines) == 0

    def test_scrape_headlines_with_area_filter(self, news_scraper):
        """Test scraping news headlines with area filter."""
        time.sleep(3)

        # Scrape news headlines for a specific area with symbol (use valid area)
        headlines = news_scraper.scrape_headlines(
            symbol='BTCUSD',
            exchange='BINANCE',
            area='americas',  # Valid area from areas.json
            sort='latest'
        )

        # Assertions
        assert headlines is not None
        assert isinstance(headlines, list)

    def test_scrape_headlines_sort_options(self, news_scraper):
        """Test different sort options for news headlines."""
        time.sleep(3)

        # Test 'latest' sort
        latest = news_scraper.scrape_headlines(
            symbol='BTCUSD',
            exchange='BINANCE',
            sort='latest'
        )
        assert latest is not None
        assert isinstance(latest, list)

        time.sleep(3)

        # Test 'most_urgent' sort
        urgent = news_scraper.scrape_headlines(
            symbol='BTCUSD',
            exchange='BINANCE',
            sort='most_urgent'
        )
        assert urgent is not None
        assert isinstance(urgent, list)
