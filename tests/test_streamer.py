"""
Comprehensive tests for the Streamer class functionality.
Tests cover: OHLC streaming, single/multiple indicators, error handling.

Set the TRADINGVIEW_JWT_TOKEN environment variable to run these tests:
    export TRADINGVIEW_JWT_TOKEN="your_jwt_token_here"
"""
import pytest
import json
import os
import time
import base64
from dotenv import load_dotenv
from tradingview_scraper.symbols.stream import Streamer

load_dotenv()


# Get JWT token from environment variable or auto-extract from cookie
JWT_TOKEN = os.getenv("TRADINGVIEW_JWT_TOKEN", "unauthorized_user_token")
if not JWT_TOKEN and os.getenv("TRADINGVIEW_COOKIE"):
    try:
        from tradingview_scraper.symbols.stream.auth import TradingViewAuth
        auth = TradingViewAuth()
        JWT_TOKEN = auth.get_token()
    except Exception:
        JWT_TOKEN = "unauthorized_user_token"

# Skip all tests if neither JWT token nor valid cookie+URL are available
has_jwt = bool(JWT_TOKEN)
has_cookie_and_url = bool(os.getenv("TRADINGVIEW_COOKIE") and os.getenv("TRADINGVIEW_CHART_URL"))
pytestmark = pytest.mark.skipif(
    not (has_jwt or has_cookie_and_url),
    reason="TRADINGVIEW_JWT_TOKEN environment variable not set and TRADINGVIEW_COOKIE/TRADINGVIEW_CHART_URL not available for JWT extraction. Set TRADINGVIEW_JWT_TOKEN or both TRADINGVIEW_COOKIE and TRADINGVIEW_CHART_URL to run these tests."
)


class TestStreamerOHLC:
    """Test OHLC data streaming without indicators"""
    
    def test_stream_ohlc_only(self):
        """Test streaming OHLC data without any indicators"""
        streamer = Streamer(
            export_result=True,
            export_type='json',
            websocket_jwt_token=JWT_TOKEN
        )
        
        result = streamer.stream(
            exchange="BINANCE",
            symbol="BTCUSDT",
            timeframe="1m",
            numb_price_candles=3
        )
        
        # Assertions
        assert "ohlc" in result
        assert "indicator" in result
        assert isinstance(result["ohlc"], list)
        assert isinstance(result["indicator"], dict)
        assert len(result["ohlc"]) > 0
        assert len(result["indicator"]) == 0  # No indicators requested
        
        # Sleep to avoid forbidden error
        time.sleep(2)


class TestStreamerSingleIndicator:
    """Test streaming with a single indicator"""
    
    def test_stream_with_rsi(self):
        """Test streaming OHLC data with RSI indicator"""
        streamer = Streamer(
            export_result=True,
            export_type='json',
            websocket_jwt_token=JWT_TOKEN
        )
        
        result = streamer.stream(
            exchange="BINANCE",
            symbol="BTCUSDT",
            indicators=[("STD;RSI", "37.0")],
            timeframe="1m",
            numb_price_candles=3
        )
        
        # Assertions
        assert "ohlc" in result
        assert "indicator" in result
        assert len(result["ohlc"]) > 0
        assert len(result["indicator"]) == 1
        assert "STD;RSI" in result["indicator"]
        assert isinstance(result["indicator"]["STD;RSI"], list)
        assert len(result["indicator"]["STD;RSI"]) > 0
        
        # Sleep to avoid forbidden error
        time.sleep(2)


class TestStreamerMultipleIndicators:
    """Test streaming with multiple indicators"""
    
    def test_stream_with_rsi_and_macd(self):
        """Test streaming with RSI and MACD indicators"""
        streamer = Streamer(
            export_result=True,
            export_type='json',
            websocket_jwt_token=JWT_TOKEN
        )
        
        result = streamer.stream(
            exchange="BINANCE",
            symbol="BTCUSDT",
            indicators=[("STD;RSI", "37.0"), ("STD;MACD", "31.0")],
            timeframe="1m",
            numb_price_candles=3
        )
        
        # Assertions
        assert "ohlc" in result
        assert "indicator" in result
        assert len(result["ohlc"]) > 0
        assert len(result["indicator"]) == 2
        assert "STD;RSI" in result["indicator"]
        assert "STD;MACD" in result["indicator"]
        assert isinstance(result["indicator"]["STD;RSI"], list)
        assert isinstance(result["indicator"]["STD;MACD"], list)
        assert len(result["indicator"]["STD;RSI"]) > 0
        assert len(result["indicator"]["STD;MACD"]) > 0
        
        # Sleep to avoid forbidden error
        time.sleep(2)
    
    def test_stream_with_three_indicators(self):
        """Test streaming with three indicators: RSI, MACD, and CCI
        
        Note: Free TradingView accounts are limited to 2 indicators maximum.
        This test will only receive 2 indicators (RSI and MACD), and CCI will timeout.
        The error message "❌ Unable to scrape indicator: STD;CCI" should be logged.
        """
        streamer = Streamer(
            export_result=True,
            export_type='json',
            websocket_jwt_token=JWT_TOKEN
        )
        
        result = streamer.stream(
            exchange="BINANCE",
            symbol="BTCUSDT",
            indicators=[
                ("STD;RSI", "37.0"),
                ("STD;MACD", "31.0"),
                ("STD;CCI", "37.0")
            ],
            timeframe="1m",
            numb_price_candles=3
        )
        
        # Assertions for free account (2 indicator limit)
        # We expect only 2 indicators to be received
        assert len(result["indicator"]) == 2, f"Free accounts can only stream 2 indicators, got {len(result['indicator'])}"
        assert "STD;RSI" in result["indicator"], "RSI should be present"
        assert "STD;MACD" in result["indicator"], "MACD should be present"
        
        # Sleep to avoid forbidden error
        time.sleep(2)


class TestStreamerDataStructure:
    """Test data structure and content validation"""
    
    def test_ohlc_data_structure(self):
        """Test that OHLC data has correct structure"""
        streamer = Streamer(
            export_result=True,
            export_type='json',
            websocket_jwt_token=JWT_TOKEN
        )
        
        result = streamer.stream(
            exchange="BINANCE",
            symbol="BTCUSDT",
            timeframe="1m",
            numb_price_candles=3
        )
        
        # Check OHLC structure
        ohlc_candle = result["ohlc"][0]
        required_keys = ['index', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
        for key in required_keys:
            assert key in ohlc_candle, f"Missing key: {key}"
        
        # Sleep to avoid forbidden error
        time.sleep(2)
    
    def test_indicator_data_structure(self):
        """Test that indicator data has correct structure"""
        streamer = Streamer(
            export_result=True,
            export_type='json',
            websocket_jwt_token=JWT_TOKEN
        )
        
        result = streamer.stream(
            exchange="BINANCE",
            symbol="BTCUSDT",
            indicators=[("STD;RSI", "37.0")],
            timeframe="1m",
            numb_price_candles=3
        )
        
        # Check indicator structure
        rsi_data = result["indicator"]["STD;RSI"][0]
        assert 'index' in rsi_data
        assert 'timestamp' in rsi_data
        assert isinstance(rsi_data['timestamp'], (int, float))
        
        # Sleep to avoid forbidden error
        time.sleep(2)


class TestStreamerErrorHandling:
    """Test error handling scenarios"""
    
    def test_expired_jwt_token_raises_error(self):
        """Test that providing an expired JWT token directly raises RuntimeError"""
        # Create an expired JWT token (exp set to past time)
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {"exp": int(time.time()) - 3600}  # Expired 1 hour ago
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "random_signature_for_testing"  # Random signature since we're not verifying
        expired_token = f"{header_b64}.{payload_b64}.{signature}"
        
        streamer = Streamer(
            export_result=True,
            export_type='json',
            websocket_jwt_token=expired_token
        )
        
        # Should raise RuntimeError for expired token provided directly
        with pytest.raises(RuntimeError, match="Provided JWT token is expired"):
            streamer.stream(
                exchange="BINANCE",
                symbol="BTCUSDT",
                indicators=[("STD;RSI", "37.0")],
                timeframe="1m",
                numb_price_candles=3
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
