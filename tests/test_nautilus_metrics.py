from unittest.mock import MagicMock

import pandas as pd
import pytest

from tradingview_scraper.portfolio_engines.nautilus_adapter import extract_nautilus_metrics


@pytest.fixture
def sample_index():
    return pd.date_range("2025-01-01", periods=5, freq="D")


def test_extract_nautilus_metrics_day1_pnl(sample_index):
    """
    Test that extract_nautilus_metrics correctly captures PnL on Day 1.
    If we start with 1000 and Day 1 ends with 1100, Day 1 return should be 10%.
    """
    initial_cash = 1000.0
    # Simulate NAV history where Day 1 already has some PnL
    # ts is in nanoseconds
    ts1 = int(sample_index[0].timestamp() * 1e9)
    ts2 = int(sample_index[1].timestamp() * 1e9)

    nav_history = [
        {"ts": ts1, "nav": 1100.0},  # Day 1 close
        {"ts": ts2, "nav": 1210.0},  # Day 2 close
    ]

    mock_strategy = MagicMock()
    mock_strategy._nav_history = nav_history

    mock_engine = MagicMock()

    metrics = extract_nautilus_metrics(mock_engine, sample_index, mock_strategy, initial_cash)

    daily_returns = metrics["daily_returns"]

    # Day 1 return should be (1100 - 1000) / 1000 = 0.1
    assert daily_returns.iloc[0] == pytest.approx(0.1)
    # Day 2 return should be (1210 - 1100) / 1100 = 0.1
    assert daily_returns.iloc[1] == pytest.approx(0.1)


def test_extract_nautilus_metrics_handles_missing_nav(sample_index):
    """
    Test that it returns 0.0 returns instead of NaN if nav history is empty.
    """
    mock_strategy = MagicMock()
    mock_strategy._nav_history = []
    mock_engine = MagicMock()

    metrics = extract_nautilus_metrics(mock_engine, sample_index, mock_strategy, 1000.0)
    assert not metrics["daily_returns"].isna().any()
    assert (metrics["daily_returns"] == 0.0).all()
