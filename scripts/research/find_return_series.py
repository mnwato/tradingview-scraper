import json

path = "artifacts/summaries/runs/20260109-135050/data/tournament_results.json"
with open(path) as f:
    data = json.load(f)

# Use vectorbt/cvxportfolio results for consistency
results = data["results"]["vectorbt"]["cvxportfolio"]


def calculate_drawdown(series):
    cum_ret = (1 + series).cumprod()
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / (running_max + 1e-12)
    return drawdown


profiles_dd = {}

# Concatenate window returns for each profile
for profile, p_data in results.items():
    if "windows" not in p_data:
        continue

    # Each window has daily_returns if we're lucky, but tournament_results.json
    # usually only has window-level metrics.
    # Wait, cumulative returns are stored in a different place or we need to rebuild them.
    # Actually, the returns are saved in the results file if 'daily_returns' was included.
    # Let me check if tournament_results.json has 'returns' as a list.
    pass

# Alternative: the file 'artifacts/summaries/runs/20260109-135050/data/cumulative_returns.pkl' might exist?
# No, grep showed returns are inside the JSON under 'summary' or similar.

# Let's try to find the actual return series.
# The `backtest_engine.py` returns them in the function result, but where are they saved?
# They are saved in `artifacts/summaries/runs/<RUN_ID>/data/portfolio_returns_final.pkl` maybe?

import os

data_dir = "artifacts/summaries/runs/20260109-135050/data"
files = os.listdir(data_dir)
print(f"Files in data dir: {files}")

# Check if there is a 'tournament_returns.pkl' or similar
for f in files:
    if "returns" in f:
        print(f"Found returns file: {f}")
