from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tradingview_scraper.portfolio_engines.nautilus_adapter import run_nautilus_backtest


@pytest.fixture
def sample_data():
    dates = pd.date_range("2025-01-01", periods=5, freq="D")
    returns = pd.DataFrame(
        {
            "BINANCE:BTCUSDT": [0.01] * 5,
        },
        index=dates,
    )
    weights = pd.DataFrame({"Symbol": ["BINANCE:BTCUSDT"], "Weight": [1.0]})
    return returns, weights


def test_adapter_fallback(sample_data):
    returns, weights = sample_data

    # Force fallback path
    with patch("tradingview_scraper.portfolio_engines.nautilus_adapter.HAS_NAUTILUS", False):
        res = run_nautilus_backtest(returns=returns, weights_df=weights, initial_holdings=None, settings=MagicMock())

        # Should return standard result from ReturnsSimulator
        assert "daily_returns" in res
        assert "sharpe" in res


def test_adapter_wiring_mocked(sample_data):
    returns, weights = sample_data

    # We mock the components imported in the adapter
    # Use patch.dict or create=True to mock things that don't exist
    with (
        patch("tradingview_scraper.portfolio_engines.nautilus_adapter.HAS_NAUTILUS", True),
        patch("tradingview_scraper.portfolio_engines.nautilus_adapter.BacktestEngine", create=True) as mock_engine_cls,
        patch("tradingview_scraper.portfolio_engines.nautilus_adapter.BacktestEngineConfig", create=True),
        patch("tradingview_scraper.portfolio_engines.nautilus_adapter.Venue", create=True),
        patch("tradingview_scraper.portfolio_engines.nautilus_adapter.NautilusRebalanceStrategy", create=True),
    ):
        mock_engine = mock_engine_cls.return_value

        res = run_nautilus_backtest(returns=returns, weights_df=weights, initial_holdings=None, settings=MagicMock())

        assert mock_engine.add_venue.called
        assert mock_engine.add_instrument.called
        assert mock_engine.run.called
