import os

import pandas as pd

folder = "artifacts/summaries/runs/20260109-135050/data/returns/"
profiles = ["benchmark", "hrp", "min_variance", "barbell"]
sim_eng = "custom_custom"

data = {}
for p in profiles:
    path = os.path.join(folder, f"{sim_eng}_{p}.pkl")
    if os.path.exists(path):
        data[p] = pd.read_pickle(path)

df = pd.DataFrame(data)
crash_date = "2025-10-10"
if crash_date in df.index:
    print(f"Returns on {crash_date}:")
    print(df.loc[crash_date])
else:
    print(f"Crash date {crash_date} not in index.")
    # Find the closest date
    idx = df.index[df.index < crash_date][-1]
    print(f"Returns on closest date {idx}:")
    print(df.loc[idx])
