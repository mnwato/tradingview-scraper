import numpy as np
import pandas as pd
import vectorbt as vbt


def debug():
    dates = pd.date_range("2025-01-01", periods=21)
    returns = pd.DataFrame({"A": [0.01] * 21}, index=dates)
    weights = pd.Series({"A": 1.0})

    # 1. Price Construction (Start at 1.0)
    prices = (1.0 + returns).cumprod().shift(1).fillna(1.0)

    # 2. Weights at t0
    w_df = pd.DataFrame(np.nan, columns=weights.index, index=prices.index)
    w_df.iloc[0] = weights.values

    portfolio = vbt.Portfolio.from_orders(close=prices, size=w_df, size_type="target_percent", freq="D", init_cash=100.0, cash_sharing=True, group_by=True)

    # 3. Shift Returns
    raw_rets = portfolio.returns()
    shifted_rets = raw_rets.shift(-1)

    print("Shifted Returns head:")
    print(shifted_rets.head())

    # Take first 20 days
    final_rets = shifted_rets.iloc[:20]
    total_ret = (1 + final_rets).prod() - 1

    print(f"\nTotal Return (20 days): {total_ret:.6f}")
    print(f"Expected:               {(1.01**20 - 1):.6f}")


if __name__ == "__main__":
    debug()
