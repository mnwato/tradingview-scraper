# tests/test_indicators.py

import os
import sys
from unittest import mock

import pytest

path = str(os.getcwd())
if path not in sys.path:
    sys.path.append(path)

from tradingview_scraper.symbols.technicals import Indicators


class TestIndicators:
    def setup_method(self):
        """Setup method to create an Indicators instance."""
        self.indicators_scraper = Indicators(export_result=True, export_type="json")

    def test_scrape_indicators_success(self):
        """Test scraping indicators successfully."""
        mock_response = {"status": "success", "data": {"RSI": 50.0, "Stoch.K": 80.0}}
        with mock.patch.object(self.indicators_scraper, "scrape", return_value=mock_response):
            indicators = self.indicators_scraper.scrape(exchange="BINANCE", symbol="BTCUSD", timeframe="1d", indicators=["RSI", "Stoch.K"])

        assert indicators == mock_response
        assert indicators["status"] == "success"
        assert "data" in indicators
        assert "RSI" in indicators["data"]
        assert "Stoch.K" in indicators["data"]
        assert indicators["data"]["RSI"] == 50.0
        assert indicators["data"]["Stoch.K"] == 80.0

    def test_scrape_indicators_invalid_exchange(self):
        """Test scraping indicators with an invalid exchange."""
        with mock.patch.object(self.indicators_scraper, "scrape", side_effect=ValueError("Invalid exchange")):
            with pytest.raises(ValueError, match="Invalid exchange"):
                self.indicators_scraper.scrape(exchange="INVALID_EXCHANGE", symbol="BTCUSD", timeframe="1d", indicators=["RSI", "Stoch.K"])

    def test_scrape_indicators_empty_response(self):
        """Test scraping indicators returns empty response."""
        with mock.patch.object(self.indicators_scraper, "scrape", return_value={}):
            indicators = self.indicators_scraper.scrape(exchange="BINANCE", symbol="BTCUSD", timeframe="1d", indicators=["RSI", "Stoch.K"])

        assert indicators == {}

    def test_scrape_indicators_valid_response(self):
        """Test scraping indicators with a valid success response."""
        valid_response = {"status": "success", "data": {"RSI": 50.0, "Stoch.K": 80.0}}
        with mock.patch.object(self.indicators_scraper, "scrape", return_value=valid_response):
            indicators = self.indicators_scraper.scrape(exchange="BINANCE", symbol="BTCUSD", timeframe="1d", indicators=["RSI", "Stoch.K"])

        assert indicators["status"] == "success"
        assert "data" in indicators
        assert "RSI" in indicators["data"]
        assert "Stoch.K" in indicators["data"]
        assert indicators["data"]["RSI"] == 50.0
        assert indicators["data"]["Stoch.K"] == 80.0
