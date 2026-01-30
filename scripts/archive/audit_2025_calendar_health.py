import os

import pandas as pd


def audit_2025_calendar_health():
    returns_path = "data/lakehouse/portfolio_returns.pkl"
    if not os.path.exists(returns_path):
        print("Returns file not found.")
        return

    df = pd.read_pickle(returns_path)

    # 1. Total Gap Count per asset
    # Gaps are represented as 0.0 in our returns matrix (filled during prep)
    gaps = (df == 0).sum()

    # 2. Identify 'Systemic Gaps' (Market Holidays)
    # Days where > 80% of assets have 0 returns
    zero_ratio = (df == 0).mean(axis=1)
    systemic_gaps = zero_ratio[zero_ratio > 0.8]

    print("--- 2025 Calendar Health Audit ---")
    print(f"Total Trading Days in Matrix: {len(df)}")
    print(f"Potential Market Holidays (Systemic Gaps): {len(systemic_gaps)}")
    for date, ratio in systemic_gaps.items():
        print(f"  - {date}: {ratio:.1%} assets zero")

    # 3. Idiosyncratic Gaps (Actual missing data)
    print("\n--- Idiosyncratic Gap Audit (Excluding systemic) ---")
    systemic_dates = systemic_gaps.index

    for symbol in df.columns:
        # Check gaps NOT on systemic dates
        idiosyncratic = df[symbol].drop(systemic_dates)
        gap_count = (idiosyncratic == 0).sum()
        if gap_count > 5:
            print(f"- {symbol}: {gap_count} unexpected gaps")


if __name__ == "__main__":
    audit_2025_calendar_health()
