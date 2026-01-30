import numpy as np
import pandas as pd
import vectorbt as vbt


def debug_vbt():
    dates = pd.date_range("2025-01-01", periods=5)
    returns = pd.DataFrame({"A": [0.01] * 5, "B": [0.01] * 5}, index=dates)
    weights = pd.Series({"A": 0.5, "B": 0.5})

    # Current implementation logic
    prices = (1.0 + returns).cumprod()

    w_df = pd.DataFrame(np.nan, columns=weights.index, index=prices.index)
    w_df.iloc[0] = weights.values

    portfolio = vbt.Portfolio.from_orders(close=prices, size=w_df, size_type="target_percent", freq="D", init_cash=100.0, group_by=False)

    print("Individual Returns:\n", portfolio.returns())
    print("\nIndividual Total Return:\n", portfolio.total_return())

    portfolio_grouped = vbt.Portfolio.from_orders(close=prices, size=w_df, size_type="target_percent", freq="D", init_cash=100.0, group_by=True)
    print("\nGrouped Returns:\n", portfolio_grouped.returns())
    print("\nGrouped Total Return:", portfolio_grouped.total_return())


if __name__ == "__main__":
    debug_vbt()
