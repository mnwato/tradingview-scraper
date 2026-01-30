import numpy as np
import pandas as pd
import vectorbt as vbt


def debug():
    # 21 days (N=20 + 1 extended)
    dates = pd.date_range("2025-01-01", periods=21)
    # 1% daily return
    returns = pd.DataFrame({"A": [0.01] * 21}, index=dates)

    weights = pd.Series({"A": 1.0})

    # Proposed Price Construction
    prices = (1.0 + returns).cumprod().shift(1).fillna(1.0)

    print("Prices head:")
    print(prices.head())
    print("Prices tail:")
    print(prices.tail())

    # Weights at t0
    w_df = pd.DataFrame(np.nan, columns=weights.index, index=prices.index)
    w_df.iloc[0] = weights.values

    portfolio = vbt.Portfolio.from_orders(close=prices, size=w_df, size_type="target_percent", freq="D", init_cash=100.0, cash_sharing=True, group_by=True)

    p_rets = portfolio.returns()
    print("\nPortfolio Returns head:")
    print(p_rets.head())

    # We expect 20 returns of 0.01 (indices t0...t19)
    # The return at t0 should be 0.01 (from price 1.0 to 1.01)

    # Check total return for first 20 days
    # (1.01^20) - 1 = 0.22019

    # VBT returns series length will be 21.
    # r[0] should be (1.01 - 1.0)/1.0 = 0.01.

    total_ret_20 = (1 + p_rets.iloc[:20]).prod() - 1
    print(f"\nTotal Return (First 20 days): {total_ret_20:.6f}")
    print(f"Expected:                   {(1.01**20 - 1):.6f}")


if __name__ == "__main__":
    debug()
