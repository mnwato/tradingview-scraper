import json

import pandas as pd

path = "artifacts/summaries/runs/20260109-135050/data/tournament_results.json"
with open(path) as f:
    data = json.load(f)

results = data["results"]["custom"]["custom"]


def calculate_max_drawdown(rets):
    cum_ret = (1 + pd.Series(rets)).cumprod()
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / (running_max + 1e-12)
    return drawdown.min(), drawdown.idxmin()


for profile, p_data in results.items():
    if "summary" not in p_data:
        continue

    # We need the daily returns to see the trail
    # They are not in the JSON usually.
    print(f"Profile: {profile}, MaxDD: {p_data['summary']['max_drawdown']}")

# Let's check the pkl files in the returns directory for custom_custom
import os

folder = "artifacts/summaries/runs/20260109-135050/data/returns/"
for profile in ["benchmark", "hrp", "min_variance", "barbell"]:
    fname = f"custom_custom_{profile}.pkl"
    path = os.path.join(folder, fname)
    if os.path.exists(path):
        rets = pd.read_pickle(path)
        dd, idx = calculate_max_drawdown(rets)
        print(f"File: {fname}, MaxDD: {dd:.6%}, At: {rets.index[idx]}")
