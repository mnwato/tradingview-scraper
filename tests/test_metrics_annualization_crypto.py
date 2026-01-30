import math

import pandas as pd
import pytest


def test_crypto_short_window_uses_365_annualization_when_weekends_present():
    """
    Spec-driven requirement:
    - Crypto sleeves (24x7) must use 365-day annualization.
    - This must hold even for short walk-forward windows (n_obs < 30).
    """
    from tradingview_scraper.utils.metrics import calculate_performance_metrics

    # Daily index includes weekends.
    idx = pd.date_range("2026-01-01", periods=10, freq="D")
    rets = pd.Series([0.001, -0.0005, 0.002, 0.0, 0.001, -0.001, 0.0007, 0.0012, -0.0003, 0.0004], index=idx, name="BINANCE:BTCUSDT")

    m = calculate_performance_metrics(rets)
    assert m["ann_factor"] == pytest.approx(365.0)

    expected_ann_return = float(rets.mean()) * 365.0
    assert m["annualized_return"] == pytest.approx(expected_ann_return)

    expected_ann_vol = float(rets.std()) * math.sqrt(365.0)
    assert m["annualized_vol"] == pytest.approx(expected_ann_vol)


def test_crypto_short_window_uses_365_annualization_when_name_is_usdt():
    """
    Spec-driven requirement:
    - Crypto sleeves should use 365-day annualization even if the sampled window
      doesn't include weekends (e.g. inner-join windows).
    - Naming convention (USDT/USDC) is treated as crypto and should force 365.
    """
    from tradingview_scraper.utils.metrics import calculate_performance_metrics

    # Business-day index has no weekends, but name implies crypto.
    idx = pd.date_range("2026-01-05", periods=10, freq="B")
    rets = pd.Series([0.001] * 10, index=idx, name="BINANCE:ETHUSDT")

    m = calculate_performance_metrics(rets)
    assert m["ann_factor"] == pytest.approx(365.0)

    expected_ann_return = float(rets.mean()) * 365.0
    assert m["annualized_return"] == pytest.approx(expected_ann_return)

    expected_ann_vol = float(rets.std()) * math.sqrt(365.0)
    assert m["annualized_vol"] == pytest.approx(expected_ann_vol)
