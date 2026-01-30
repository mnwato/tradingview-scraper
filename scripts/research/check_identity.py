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
print("First 10 days of returns:")
print(df.head(10))

print("\nAre benchmark and hrp identical?")
print((df["benchmark"] == df["hrp"]).all())

print("\nCorrelation matrix:")
print(df.corr())
