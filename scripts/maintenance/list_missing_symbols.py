import json
import os

import pandas as pd

LAKEHOUSE_PATH = "data/lakehouse"
CANDIDATES_FILE = os.path.join(LAKEHOUSE_PATH, "portfolio_candidates.json")
RETURNS_FILE = os.path.join(LAKEHOUSE_PATH, "portfolio_returns.pkl")


def get_missing_symbols():
    with open(CANDIDATES_FILE, "r") as f:
        candidates = json.load(f)
    candidate_symbols = [c["symbol"] for c in candidates]

    try:
        returns_df = pd.read_pickle(RETURNS_FILE)
        matrix_symbols = returns_df.columns.tolist()
    except Exception:
        matrix_symbols = []

    missing = [s for s in candidate_symbols if s not in matrix_symbols]
    print(json.dumps(missing))


if __name__ == "__main__":
    get_missing_symbols()
