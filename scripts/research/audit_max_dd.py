import os

import pandas as pd

folder = "artifacts/summaries/runs/20260109-135050/data/returns/"
files = ["vectorbt_market_benchmark.pkl", "vectorbt_skfolio_barbell.pkl", "vectorbt_skfolio_hrp.pkl", "vectorbt_skfolio_min_variance.pkl"]


def calculate_max_drawdown(rets):
    cum_ret = (1 + rets).cumprod()
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / (running_max + 1e-12)
    return drawdown.min(), drawdown.idxmin()


print(f"{'Profile':30} | {'MaxDD':>8} | {'Date'}")
print("-" * 50)

for f in files:
    path = os.path.join(folder, f)
    if os.path.exists(path):
        rets = pd.read_pickle(path)
        # Ensure index is datetime
        rets.index = pd.to_datetime(rets.index)
        dd, date = calculate_max_drawdown(rets)
        print(f"{f:30} | {dd:8.2%} | {date}")
    else:
        print(f"{f:30} | NOT FOUND")
