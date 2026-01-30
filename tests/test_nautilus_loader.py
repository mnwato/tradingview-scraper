import pandas as pd
import pytest

from tradingview_scraper.portfolio_engines.nautilus_loader import NautilusDataConverter


@pytest.fixture
def sample_returns():
    dates = pd.date_range("2025-01-01", periods=5, freq="D")
    df = pd.DataFrame({"BINANCE:BTCUSDT": [0.01, -0.02, 0.015, 0.005, -0.01], "BINANCE:ETHUSDT": [0.02, -0.01, 0.03, -0.02, 0.01]}, index=dates)
    return df


def test_data_synthesis(sample_returns):
    converter = NautilusDataConverter()
    bars = converter.to_nautilus_bars(sample_returns)

    assert "BINANCE:BTCUSDT" in bars
    btc_bars = bars["BINANCE:BTCUSDT"]
    assert len(btc_bars) == 5

    # Check if first bar price is roughly 101.0 (assuming start at 100.0)
    # Price(t) = Price(t-1) * (1 + Ret(t))
    assert round(btc_bars[0]["close"], 2) == 101.0
    assert round(btc_bars[1]["close"], 2) == 98.98  # 101 * 0.98
