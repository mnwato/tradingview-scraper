from unittest.mock import MagicMock

import pandas as pd

from tradingview_scraper.portfolio_engines import nautilus_strategy


# Mocking classes
class MockInstrumentId:
    def __init__(self, symbol):
        self.symbol = symbol
        self.venue = "BACKTEST"

    def __str__(self):
        return f"{self.symbol}.BACKTEST"


class MockBar:
    def __init__(self, close):
        self.close = float(close)
        self.ts_event = 100
        # Add float_value method to mimic Nautilus object behavior
        self.close_obj = MagicMock()
        self.close_obj.float_value.return_value = float(close)


def test_calculate_target_qty_short():
    """Test that _calculate_target_qty handles negative weights correctly."""

    # Setup
    weights = pd.DataFrame({"BTC.BACKTEST": [-0.5]}, index=[pd.Timestamp("2024-01-01", tz="UTC")])
    strategy = nautilus_strategy.NautilusRebalanceStrategy(target_weights=weights)

    class MockCatalog:
        def get_limits(self, symbol, venue):
            limits = MagicMock()
            limits.step_size = 0.001
            limits.min_notional = 10.0
            return limits

    strategy.catalog = MockCatalog()

    # Mock _get_nav to return 1000
    strategy._get_nav = MagicMock(return_value=1000.0)

    # Mock methods used in _from_nautilus_id_str
    strategy._from_nautilus_id_str = lambda x: x.split(".")[0] + ":BACKTEST"

    # Inputs
    instrument = MagicMock()
    instrument.id = MockInstrumentId("BTC")

    # Mock bar with float_value
    bar = MagicMock()
    bar.close.float_value.return_value = 100.0

    # Execution
    # weight = -0.5. NAV = 1000. Target Val = 1000 * -0.5 * 0.95 = -475.
    # Price = 100. Raw Qty = -4.75.
    # Step = 0.001.
    # Qty = trunc(-4.75 / 0.001) * 0.001 = -4.75.
    # Notional check: abs(-4.75) * 100 = 475 > 10. OK.

    qty = strategy._calculate_target_qty(instrument, bar, -0.5)

    assert qty == -4.75


def test_calculate_target_qty_rounding_towards_zero():
    """Test rounding towards zero for negative quantities."""
    weights = pd.DataFrame({"BTC.BACKTEST": [0.0]}, index=[pd.Timestamp("2024-01-01", tz="UTC")])
    strategy = nautilus_strategy.NautilusRebalanceStrategy(target_weights=weights)

    class MockCatalog:
        def get_limits(self, symbol, venue):
            limits = MagicMock()
            limits.step_size = 1.0  # Large step to verify rounding
            limits.min_notional = 0.0
            return limits

    strategy.catalog = MockCatalog()
    strategy._get_nav = MagicMock(return_value=100.0)
    strategy._from_nautilus_id_str = lambda x: x

    instrument = MagicMock()
    instrument.id = MockInstrumentId("BTC")

    bar = MagicMock()
    bar.close.float_value.return_value = 10.0

    # Case 1: Positive 1.9 -> 1.0
    # weight 0.19. Target = 19. Qty = 1.9.
    # Using 0.2 to get exactly 1.9
    # target = 100 * 0.2 * 0.95 = 19.
    # raw = 1.9. trunc = 1.
    qty = strategy._calculate_target_qty(instrument, bar, 0.2)
    assert qty == 1.0

    # Case 2: Negative -1.9 -> -1.0 (Not -2.0)
    qty = strategy._calculate_target_qty(instrument, bar, -0.2)
    assert qty == -1.0
