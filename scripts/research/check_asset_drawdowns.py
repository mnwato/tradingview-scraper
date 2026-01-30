import pandas as pd

# Load the returns
rets = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")

# Calculate MaxDD for each asset
max_dds = {}
for col in rets.columns:
    cum_ret = (1 + rets[col]).cumprod()
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / (running_max + 1e-12)
    max_dds[col] = float(drawdown.min())

print("Max Drawdown per asset:")
for sym, dd in sorted(max_dds.items(), key=lambda x: x[1]):
    print(f"{sym:30}: {dd:.2%}")

# Check if there is a day with massive crash
worst_day = rets.mean(axis=1).idxmin()
print(f"\nWorst day (mean): {worst_day}")
print(f"Mean return on that day: {rets.loc[worst_day].mean():.2%}")
print("\nReturns on that day:")
print(rets.loc[worst_day].sort_values().head(10))
