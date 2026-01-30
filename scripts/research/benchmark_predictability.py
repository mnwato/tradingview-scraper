import os

import pandas as pd

from tradingview_scraper.utils.predictability import calculate_autocorrelation, calculate_ljungbox_pvalue


def benchmark_self_predictability():
    returns_path = "data/lakehouse/portfolio_returns_raw.pkl"
    if not os.path.exists(returns_path):
        print("Required data files not found in lakehouse.")
        return

    returns = pd.read_pickle(returns_path).fillna(0.0)

    print("--- Self-Predictability Benchmark (ACF & Ljung-Box) ---")

    results = []
    for symbol in returns.columns:
        x = returns[symbol].to_numpy()
        acf1 = calculate_autocorrelation(x, lag=1)
        acf5 = calculate_autocorrelation(x, lag=5)
        lb_p = calculate_ljungbox_pvalue(x, lags=5)

        results.append({"Symbol": symbol, "ACF_Lag1": acf1, "ACF_Lag5": acf5, "LB_PValue": lb_p, "Predictable": lb_p < 0.05})

    df = pd.DataFrame(results).sort_values("ACF_Lag1", ascending=False)
    print(df.to_markdown(index=False))

    print(f"\nTotal assets analyzed: {len(df)}")
    print(f"Statistically Predictable (p < 0.05): {df['Predictable'].sum()}")


if __name__ == "__main__":
    benchmark_self_predictability()
