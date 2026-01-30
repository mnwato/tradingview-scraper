from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tradingview_scraper.portfolio_engines.nautilus_strategy import NautilusRebalanceStrategy


@pytest.fixture
def mock_strategy_config():
    dates = pd.date_range("2025-01-01", periods=5, freq="D")
    weights = pd.DataFrame({"BINANCE:BTCUSDT": [0.5, 0.5, 0.4, 0.4, 0.6], "BINANCE:ETHUSDT": [0.5, 0.5, 0.6, 0.6, 0.4]}, index=dates)
    return weights


def test_rebalance_logic(mock_strategy_config):
    # We mock the Nautilus Strategy base class since we don't want to run a full engine here
    with patch("tradingview_scraper.portfolio_engines.nautilus_strategy.HAS_NAUTILUS", False):
        strategy = NautilusRebalanceStrategy(target_weights=mock_strategy_config)

        # Mock Nautilus internal state
        strategy.portfolio = MagicMock()
        strategy.portfolio.nav = 100000.0

        # Test target quantity calculation for BTC at t=0
        # Weight = 0.5, NAV = 100000 -> Target Value = 5000
        # Price = 100 -> Target Qty = 50

        mock_bar = MagicMock()
        mock_bar.ts = mock_strategy_config.index[0]
        mock_bar.close = 100.0

        mock_instrument = MagicMock()
        mock_instrument.id = "BINANCE:BTCUSDT"

        # Precision mock
        strategy.catalog = MagicMock()
        mock_limits = MagicMock()
        mock_limits.step_size = 0.01
        mock_limits.min_notional = 10.0
        strategy.catalog.get_limits.return_value = mock_limits

        qty = strategy._calculate_target_qty(mock_instrument, mock_bar, weight=0.5)
        assert qty == pytest.approx(500.0)  # 100000 * 0.5 / 100 = 500

        # Test Rounding
        mock_limits.step_size = 1.0
        qty_rounded = strategy._calculate_target_qty(mock_instrument, mock_bar, weight=0.5)
        assert qty_rounded == pytest.approx(500.0)

        # Test floor rounding
        mock_limits.step_size = 1000.0
        qty_floor = strategy._calculate_target_qty(mock_instrument, mock_bar, weight=0.5)
        print(f"DEBUG: qty_floor={qty_floor}")
        assert qty_floor == 0.0
