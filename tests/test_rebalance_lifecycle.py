import pandas as pd
import pytest

from tradingview_scraper.portfolio_engines.backtest_simulators import CVXPortfolioSimulator, ReturnsSimulator, VectorBTSimulator, _calculate_standard_turnover
from tradingview_scraper.settings import get_settings


@pytest.fixture
def sample_data():
    dates = pd.date_range("2025-01-01", periods=21)  # N+1 for alignment
    # Asset A goes up 10% daily, B goes down 10% daily
    returns = pd.DataFrame({"A": [0.1] * 21, "B": [-0.1] * 21}, index=dates)
    weights_df = pd.DataFrame([{"Symbol": "A", "Weight": 0.5}, {"Symbol": "B", "Weight": 0.5}])
    return returns, weights_df


def test_returns_simulator_window_vs_daily(sample_data):
    returns, weights_df = sample_data
    sim = ReturnsSimulator()

    # 1. Window Mode
    res_window = sim.simulate(returns, weights_df, initial_holdings=pd.Series({"A": 0.5, "B": 0.5, "cash": 0.0}))

    # 2. Daily Mode
    settings = get_settings()
    settings.features.feat_rebalance_mode = "daily"
    res_daily = sim.simulate(returns, weights_df, initial_holdings=pd.Series({"A": 0.5, "B": 0.5, "cash": 0.0}))
    settings.features.feat_rebalance_mode = "window"

    # Window mode: Winner A grows, loser B shrinks. Portfolio return > 0.
    # Daily mode: Rebalance to 50/50. 0.5*0.1 + 0.5*-0.1 = 0 return.
    assert res_window["total_return"] > res_daily["total_return"]
    assert res_window["total_return"] > 0.01


def test_cvx_simulator_window_vs_daily(sample_data):
    returns, weights_df = sample_data
    sim = CVXPortfolioSimulator()

    res_window = sim.simulate(returns, weights_df, initial_holdings=pd.Series({"A": 0.5, "B": 0.5, "cash": 0.0}))

    settings = get_settings()
    settings.features.feat_rebalance_mode = "daily"
    res_daily = sim.simulate(returns, weights_df, initial_holdings=pd.Series({"A": 0.5, "B": 0.5, "cash": 0.0}))
    settings.features.feat_rebalance_mode = "window"

    assert res_window["total_return"] > res_daily["total_return"]


def test_vbt_simulator_window_vs_daily(sample_data):
    returns, weights_df = sample_data
    sim = VectorBTSimulator()

    res_window = sim.simulate(returns, weights_df, initial_holdings=pd.Series({"A": 0.5, "B": 0.5, "cash": 0.0}))

    settings = get_settings()
    settings.features.feat_rebalance_mode = "daily"
    res_daily = sim.simulate(returns, weights_df, initial_holdings=pd.Series({"A": 0.5, "B": 0.5, "cash": 0.0}))
    settings.features.feat_rebalance_mode = "window"

    assert res_window["total_return"] > res_daily["total_return"]


def test_turnover_standardization():
    w_target = pd.Series({"A": 0.6, "B": 0.4})
    h_init = pd.Series({"A": 0.5, "B": 0.5})
    t = _calculate_standard_turnover(w_target, h_init)
    assert pytest.approx(t) == 0.1
