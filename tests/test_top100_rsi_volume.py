from unittest import mock

from tradingview_scraper.screeners.top100_rsi_volume import (
    DEFAULT_COLUMNS_BASE,
    screen_top100_oversold_with_rising_volume,
)


def test_screen_uses_primary_volume_average_field():
    mock_screener = mock.Mock()
    mock_screener.screen.return_value = {
        "status": "success",
        "data": [{"symbol": "NASDAQ:AAPL"}],
        "total": 1,
    }

    result = screen_top100_oversold_with_rising_volume(screener=mock_screener)

    assert result["status"] == "success"
    assert result["volume_average_field"] == "average_volume_20d_calc"

    mock_screener.screen.assert_called_once()
    _, kwargs = mock_screener.screen.call_args
    assert kwargs["market"] == "america"
    assert kwargs["sort_by"] == "market_cap_basic"
    assert kwargs["sort_order"] == "desc"
    assert kwargs["limit"] == 5000
    assert kwargs["columns"] == [*DEFAULT_COLUMNS_BASE, "average_volume_20d_calc"]
    assert kwargs.get("filters") in (None, [])


def test_universe_is_restricted_to_nasdaq_and_nyse_before_signal_filter():
    mock_screener = mock.Mock()
    mock_screener.screen.return_value = {
        "status": "success",
        "data": [
            {
                "symbol": "OTC:AAA",
                "market_cap_basic": 900,
                "RSI": 20,
                "volume": 100,
                "average_volume_20d_calc": 10,
            },
            {
                "symbol": "NASDAQ:BBB",
                "market_cap_basic": 800,
                "RSI": 20,
                "volume": 100,
                "average_volume_20d_calc": 10,
            },
            {
                "symbol": "NYSE:CCC",
                "market_cap_basic": 700,
                "RSI": 35,
                "volume": 100,
                "average_volume_20d_calc": 10,
            },
            {
                "symbol": "NYSE:DDD",
                "market_cap_basic": 600,
                "RSI": 25,
                "volume": 5,
                "average_volume_20d_calc": 10,
            },
        ],
        "total": 4,
    }

    result = screen_top100_oversold_with_rising_volume(
        screener=mock_screener, limit=2, include_universe=True
    )

    assert result["status"] == "success"
    assert result["universe_size"] == 2
    assert [row["symbol"] for row in result["universe"]] == ["NASDAQ:BBB", "NYSE:CCC"]
    assert [row["symbol"] for row in result["data"]] == ["NASDAQ:BBB"]


def test_response_excludes_universe_by_default():
    mock_screener = mock.Mock()
    mock_screener.screen.return_value = {
        "status": "success",
        "data": [
            {
                "symbol": "NASDAQ:BBB",
                "market_cap_basic": 800,
                "RSI": 20,
                "volume": 100,
                "average_volume_20d_calc": 10,
            }
        ],
        "total": 1,
    }

    result = screen_top100_oversold_with_rising_volume(screener=mock_screener, limit=1)

    assert result["status"] == "success"
    assert "universe" not in result
    assert "universe_size" not in result


def test_screen_falls_back_to_secondary_volume_average_field():
    mock_screener = mock.Mock()
    mock_screener.screen.side_effect = [
        {"status": "failed", "error": "invalid field average_volume_20d_calc"},
        {
            "status": "success",
            "data": [
                {
                    "symbol": "NASDAQ:MSFT",
                    "market_cap_basic": 1,
                    "RSI": 10,
                    "volume": 2,
                    "average_volume_30d_calc": 1,
                }
            ],
            "total": 1,
        },
    ]

    result = screen_top100_oversold_with_rising_volume(screener=mock_screener)

    assert result["status"] == "success"
    assert result["volume_average_field"] == "average_volume_30d_calc"
    assert mock_screener.screen.call_count == 2

    _, first_kwargs = mock_screener.screen.call_args_list[0]
    _, second_kwargs = mock_screener.screen.call_args_list[1]
    assert first_kwargs["columns"] == [*DEFAULT_COLUMNS_BASE, "average_volume_20d_calc"]
    assert second_kwargs["columns"] == [*DEFAULT_COLUMNS_BASE, "average_volume_30d_calc"]


def test_screen_returns_failure_after_all_fallbacks():
    mock_screener = mock.Mock()
    mock_screener.screen.side_effect = [
        {"status": "failed", "error": "invalid field"},
        {"status": "failed", "error": "still invalid"},
        {"status": "failed", "error": "also invalid"},
    ]

    result = screen_top100_oversold_with_rising_volume(screener=mock_screener)

    assert result["status"] == "failed"
    assert result["error"] == "screening failed for all volume average field candidates"
    assert len(result["attempts"]) == 3
