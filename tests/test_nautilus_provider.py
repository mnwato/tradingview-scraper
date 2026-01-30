import pytest

from tradingview_scraper.execution.metadata import ExecutionMetadataCatalog
from tradingview_scraper.portfolio_engines.nautilus_provider import NautilusInstrumentProvider


@pytest.fixture
def mock_catalog(tmp_path):
    catalog = ExecutionMetadataCatalog(base_path=str(tmp_path))
    catalog.upsert_limits(
        [
            {
                "symbol": "BINANCE:BTCUSDT",
                "venue": "BINANCE",
                "lot_size": 0.00001,
                "step_size": 0.00001,
                "tick_size": 0.01,
            }
        ]
    )
    return catalog


def test_instrument_mapping(mock_catalog):
    provider = NautilusInstrumentProvider(catalog=mock_catalog)
    instruments = provider.get_instruments(venue="BINANCE")

    assert "BINANCE:BTCUSDT" in instruments
    inst = instruments["BINANCE:BTCUSDT"]

    # Check Nautilus-specific mapping (if possible without full nautilus-trader import)
    # For now, let's just check the data extraction logic
    assert inst["symbol"] == "BTCUSDT"
    assert inst["price_precision"] == 2  # 0.01 -> 2
    assert inst["size_precision"] == 5  # 0.00001 -> 5
