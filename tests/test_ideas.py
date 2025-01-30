import os
import sys
import time
import pytest
from unittest import mock

# Add the current working directory to the system path
path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.ideas import Ideas

class TestIdeas:
    @pytest.fixture
    def ideas_scraper(self):
        """Fixture to create an instance of Ideas for testing."""
        return Ideas(export_result=False)

    @mock.patch('tradingview_scraper.symbols.ideas.requests.get')
    def test_scrape_recent_ideas_success(self, mock_get, ideas_scraper):
        """Test scraping recent ideas successfully."""
        # Mock response for recent ideas
        mock_response = mock.Mock()
        mock_response.text = '<div class="listContainer-rqOoE_3Q"><article><a class="title-">Recent Idea Title</a><a class="paragraph-">Recent Idea Description</a><span class="card-author-">by Recent Author</span><time class="publication-date-" datetime="2023-01-02T00:00:00Z"></time></article></div>'
        mock_get.return_value = mock_response

        # Scrape ideas
        time.sleep(3)
        ideas = ideas_scraper.scrape(symbol="NASDAQ-NDX", sort="popular", startPage=1, endPage=1)

        # Assertions to validate the scraped ideas
        assert len(ideas) == 1
        assert ideas[0]['title'] == "Recent Idea Title"
        assert ideas[0]['paragraph'] == "Recent Idea Description"
        assert ideas[0]['author'] == "Recent Author"
        assert ideas[0]['publication_datetime'] == "2023-01-02T00:00:00Z"

    @mock.patch('tradingview_scraper.symbols.ideas.requests.get')
    def test_scrape_no_ideas(self, mock_get, ideas_scraper):
        """Test handling of no ideas found."""
        # Mock response for no ideas
        mock_response = mock.Mock()
        mock_response.text = '<div class="listContainer-rqOoE_3Q"></div>'
        mock_get.return_value = mock_response

        # Attempt to scrape ideas
        time.sleep(3)
        with pytest.raises(Exception, match="No ideas found. Check the symbol or page number."):
            ideas_scraper.scrape(symbol="NASDAQ-NDX", sort="popular", startPage=1, endPage=1)

    @mock.patch('tradingview_scraper.symbols.ideas.requests.get')
    def test_scrape_invalid_sort(self, mock_get, ideas_scraper):
        """Test handling of invalid sort argument."""
        # Attempt to scrape ideas with invalid sort
        time.sleep(3)
        ideas = ideas_scraper.scrape(symbol="NASDAQ-NDX", sort="invalid_sort", startPage=1, endPage=1)

        # Check that no ideas are returned
        assert ideas == []

    def test_scrape_recent_sorting_option(self, ideas_scraper):
        """Test scraping recent ideas and validate results."""

        # Scrape recent ideas
        time.sleep(3)
        ideas = ideas_scraper.scrape(symbol="BTCUSD", sort="recent", startPage=1, endPage=1)

        # Assertions to validate the scraped ideas
        assert ideas is not None  # Check that the result is not None
        assert len(ideas) >= 1  # Check that one idea is returned


    def test_scrape_popular_sorting_option(self, ideas_scraper):
        """Test scraping recent ideas and validate results."""

        # Scrape popular ideas
        time.sleep(3)
        ideas = ideas_scraper.scrape(symbol="BTCUSD", sort="popular", startPage=1, endPage=1)

        # Assertions to validate the scraped ideas
        assert ideas is not None  # Check that the result is not None
        assert len(ideas) >= 1  # Check that one idea is returned
        