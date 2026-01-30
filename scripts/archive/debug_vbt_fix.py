import numpy as np
import pandas as pd
import vectorbt as vbt


def debug_vbt():
    dates = pd.date_range("2025-01-01", periods=20)
    returns = pd.DataFrame({"A": [0.01] * 20, "B": [0.01] * 20}, index=dates)

    weights = pd.Series({"A": 0.5, "B": 0.5})

    # Prices
    prices = (1.0 + returns).cumprod()

    # Weights dataframe
    w_df = pd.DataFrame(np.nan, columns=weights.index, index=prices.index)
    w_df.iloc[0] = weights.values

    print("--- With cash_sharing=True ---")
    try:
        portfolio = vbt.Portfolio.from_orders(close=prices, size=w_df, size_type="target_percent", freq="D", init_cash=100.0, cash_sharing=True, group_by=True)
        print("Total Return:", portfolio.total_return())
        print("Cash:", portfolio.cash().iloc[0])
        print("Value:", portfolio.value().iloc[0])
    except Exception as e:
        print(f"Error with cash_sharing=True: {e}")

    print("\n--- Current Implementation (Implicitly cash_sharing=False) ---")
    portfolio_bad = vbt.Portfolio.from_orders(close=prices, size=w_df, size_type="target_percent", freq="D", init_cash=100.0, group_by=True)
    print("Total Return:", portfolio_bad.total_return())
    # In bad case, grouping happens after. So init cash is summed?
    print("Value t=0 (Grouped):", portfolio_bad.value().iloc[0])


if __name__ == "__main__":
    debug_vbt()
