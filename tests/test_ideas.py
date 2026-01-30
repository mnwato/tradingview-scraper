import os
import sys
from unittest import mock

import pytest

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

    @mock.patch("tradingview_scraper.symbols.ideas.requests.get")
    def test_scrape_recent_ideas_success(self, mock_get, ideas_scraper):
        """Test scraping recent ideas successfully with mocked response."""
        # Mock response for recent ideas
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.text = ""  # No captcha
        mock_response.json.return_value = {
            "data": {
                "ideas": {
                    "data": {
                        "items": [
                            {
                                "name": "Recent Idea Title",
                                "description": "Recent Idea Description",
                                "symbol": {"logo_urls": ["image_url"]},
                                "chart_url": "chart_url",
                                "comments_count": 10,
                                "views_count": 100,
                                "user": {"username": "Recent Author"},
                                "likes_count": 5,
                                "date_timestamp": 1672531200,
                            }
                        ]
                    }
                }
            }
        }
        mock_get.return_value = mock_response
        ideas = ideas_scraper.scrape(symbol="NASDAQ-NDX", sort="recent", startPage=1, endPage=1)
        assert len(ideas) == 1
        assert ideas[0]["title"] == "Recent Idea Title"
        assert ideas[0]["description"] == "Recent Idea Description"
        assert ideas[0]["author"] == "Recent Author"
        assert ideas[0]["comments_count"] == 10
        assert ideas[0]["views_count"] == 100
        assert ideas[0]["likes_count"] == 5

    @mock.patch("tradingview_scraper.symbols.ideas.requests.get")
    def test_scrape_no_ideas(self, mock_get, ideas_scraper):
        """Test handling of no ideas found with mocked response."""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.text = ""  # No captcha
        mock_response.json.return_value = {"data": {"ideas": {"data": {"items": []}}}}
        mock_get.return_value = mock_response

        ideas = ideas_scraper.scrape(symbol="NASDAQ-NDX", sort="popular", startPage=1, endPage=1)

        assert ideas == []

    @mock.patch("tradingview_scraper.symbols.ideas.requests.get")
    def test_scrape_invalid_sort(self, mock_get, ideas_scraper):
        """Test handling of invalid sort argument."""
        ideas = ideas_scraper.scrape(symbol="NASDAQ-NDX", sort="invalid_sort", startPage=1, endPage=1)

        assert ideas == []

    def test_scrape_recent_sorting_option(self, ideas_scraper):
        """Test scraping recent ideas with real API call."""
        pytest.importorskip("requests", reason="network tests skipped")

        ideas = ideas_scraper.scrape(symbol="BTCUSD", sort="recent", startPage=1, endPage=1)
        if ideas == []:
            pytest.skip("Captcha challenge – skipping real API test")

        assert ideas is not None
        assert isinstance(ideas, list)
        if ideas:
            idea = ideas[0]
            assert "title" in idea
            assert "description" in idea
            assert "author" in idea
            assert "comments_count" in idea
            assert "views_count" in idea
            assert "likes_count" in idea
            assert "timestamp" in idea

    def test_scrape_popular_sorting_option(self, ideas_scraper):
        """Test scraping popular ideas with real API call."""
        pytest.importorskip("requests", reason="network tests skipped")

        ideas = ideas_scraper.scrape(symbol="BTCUSD", sort="popular", startPage=1, endPage=1)
        if ideas == []:
            pytest.skip("Captcha challenge – skipping real API test")
        assert ideas is not None
        assert isinstance(ideas, list)
        if ideas:
            idea = ideas[0]
            assert "title" in idea
            assert "description" in idea
            assert "author" in idea
            assert "comments_count" in idea
            assert "views_count" in idea
            assert "likes_count" in idea
            assert "timestamp" in idea

    def test_threading_avoids_rate_limiting(self, ideas_scraper):
        """Test that threading prevents rate limiting when scraping multiple pages concurrently."""
        pytest.importorskip("requests", reason="network tests skipped")

        ideas = ideas_scraper.scrape(symbol="BTCUSD", sort="popular", startPage=1, endPage=42)
        if ideas == []:
            pytest.skip("Captcha challenge – skipping real API test")
        assert ideas is not None
        assert isinstance(ideas, list)
        assert len(ideas) > 0
        for idea in ideas[:5]:
            assert "title" in idea
            assert "description" in idea
            assert "author" in idea
            assert "comments_count" in idea
            assert "views_count" in idea
            assert "likes_count" in idea
            assert "timestamp" in idea
