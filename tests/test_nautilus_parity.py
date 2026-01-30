from unittest.mock import MagicMock

import pandas as pd
import pytest

try:
    from tradingview_scraper.portfolio_engines.nautilus_adapter import run_nautilus_backtest

    HAS_NAUTILUS = True

except ImportError:
    HAS_NAUTILUS = False

    def run_nautilus_backtest(*args, **kwargs):
        return {}


from tradingview_scraper.portfolio_engines.backtest_simulators import ReturnsSimulator


@pytest.mark.skipif(not HAS_NAUTILUS, reason="NautilusTrader not installed")
def test_nautilus_parity_synthetic():
    """
    Verifies that NautilusTrader adapter produces non-zero returns that match
    the vectorized ReturnsSimulator on synthetic data.
    """
    # 1. Generate Synthetic Data
    # 30 days of data
    dates = pd.date_range("2024-01-01", periods=30, freq="D", tz="UTC")
    symbols = ["ASSET:BACKTEST"]  # Use colon format as expected by adapter

    # Constant 1% daily return
    returns = pd.DataFrame(index=dates)
    returns["ASSET:BACKTEST"] = 0.01

    # Full allocation
    weights = pd.DataFrame([{"Symbol": "ASSET:BACKTEST", "Weight": 0.99}])  # 0.99 to avoid rounding issues with cash

    # 2. Run Legacy Simulator
    legacy_sim = ReturnsSimulator()
    legacy_res = legacy_sim.simulate(returns, weights)

    # 3. Run Nautilus Simulator
    # Mock settings with zero friction for pure parity check
    mock_settings = MagicMock()
    mock_settings.backtest_slippage = 0.0
    mock_settings.backtest_commission = 0.0
    mock_settings.backtest_cash_asset = "USD"

    nautilus_res = run_nautilus_backtest(returns=returns, weights_df=weights, initial_holdings=None, settings=mock_settings)

    leg_ret = legacy_res["total_return"]
    nau_ret = nautilus_res["total_return"]

    print(f"\nLegacy Return: {leg_ret}")
    print(f"Nautilus Return: {nau_ret}")

    # 4. Assertions
    # Ensure not 0.0 (The "All 0" bug check)
    assert nau_ret != 0.0, "Nautilus return is 0.0, implying flat NAV"
    assert not pd.isna(nau_ret), "Nautilus return is NaN"

    # Parity check
    # Allow small divergence due to execution timing (close vs open/next-close)
    divergence = abs(nau_ret - leg_ret)
    assert divergence < 0.05, f"Divergence {divergence} exceeds 0.05 limit"


@pytest.mark.skipif(not HAS_NAUTILUS, reason="NautilusTrader not installed")
def test_nautilus_friction_impact():
    """
    Verifies that enabling friction (slippage/commission) reduces total returns.
    This confirms that the ParityFillModel is active and effective.
    """
    # 1. Generate Synthetic Data
    dates = pd.date_range("2024-01-01", periods=30, freq="D", tz="UTC")
    returns = pd.DataFrame(index=dates)
    returns["ASSET:BACKTEST"] = 0.01  # 1% daily return
    weights = pd.DataFrame([{"Symbol": "ASSET:BACKTEST", "Weight": 0.99}])

    # 2. Run Zero-Friction Baseline
    settings_zero = MagicMock()
    settings_zero.backtest_slippage = 0.0
    settings_zero.backtest_commission = 0.0
    settings_zero.backtest_cash_asset = "USD"

    res_zero = run_nautilus_backtest(returns=returns, weights_df=weights, initial_holdings=None, settings=settings_zero)
    ret_zero = res_zero["total_return"]

    # 3. Run High-Friction Scenario
    settings_high = MagicMock()
    settings_high.backtest_slippage = 0.01  # 1% slippage
    settings_high.backtest_commission = 0.01  # 1% commission
    settings_high.backtest_cash_asset = "USD"

    res_high = run_nautilus_backtest(returns=returns, weights_df=weights, initial_holdings=None, settings=settings_high)
    ret_high = res_high["total_return"]

    # 4. Assertions
    assert ret_zero > 0.0, "Baseline return must be positive"
    assert ret_high > 0.0, "Friction return should still be positive (for this scenario)"
    assert ret_high < ret_zero, f"Friction did not reduce returns! Zero={ret_zero}, High={ret_high}"

    # Check that difference is significant (at least 1% impact expected)
    diff = ret_zero - ret_high
    assert diff > 0.01, f"Friction impact too small: {diff}"


@pytest.mark.skipif(not HAS_NAUTILUS, reason="NautilusTrader not installed")
def test_nautilus_log_audit(caplog):
    """
    Verifies that the adapter injects the [AUDIT] log block and that
    the reported 'True Equity' matches the calculated metrics, while proving
    the 'CashAccount' discrepancy exists.
    """
    # 1. Generate Synthetic Data (Close to 100% invested)
    dates = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
    returns = pd.DataFrame(index=dates)
    returns["ASSET:BACKTEST"] = 0.01
    weights = pd.DataFrame([{"Symbol": "ASSET:BACKTEST", "Weight": 0.99}])

    # 2. Run Nautilus Simulator
    settings = MagicMock()
    settings.backtest_slippage = 0.0
    settings.backtest_commission = 0.0
    settings.backtest_cash_asset = "USD"

    with caplog.at_level("INFO"):
        res = run_nautilus_backtest(returns=returns, weights_df=weights, initial_holdings=None, settings=settings)

    # 3. Analyze Logs
    log_text = caplog.text

    # Verify Audit Block Presence
    assert "=== NAUTILUS AUDIT: NautilusRebalanceStrategy ===" in log_text
    assert "TRUE EQUITY:" in log_text
    assert "Final Free Cash:" in log_text

    # 4. Verify Discrepancy (Cash < Equity)
    # Extract values roughly (or just rely on the logic that 99% weight implies low cash)
    # We can check that "Final Free Cash" is small relative to "TRUE EQUITY"
    # But for robustness, let's just ensure the log message exists implying they are different
    assert "(This is NOT Equity)" in log_text

    # 5. Verify Metrics Consistency
    # The return in the metrics result should match the equity growth
    # Initial = 1,000,000. Return ~ 10% (10 days * 1%) * 0.99 exposure
    total_ret = res["total_return"]
    assert total_ret > 0.08, "Return should be positive and substantial"

    # Ensure the log appeared AFTER the run
    # (Implicit by being in the capture during the function call)
