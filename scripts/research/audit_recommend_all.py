from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression


def audit_recommend_all():
    # Load Feature Data
    base = Path("data/lakehouse/features/tv_technicals_1d")
    date_dirs = sorted(list(base.glob("date=*")))
    if not date_dirs:
        print("No data found.")
        return

    # Iterate over all parquet files in the latest partition to get maximum data points
    # (Assuming we might have ingested more than just BTC, but if not, it works with 1)
    latest_partition = date_dirs[-1]
    dfs = []
    for f in latest_partition.glob("*.parquet"):
        try:
            dfs.append(pd.read_parquet(f))
        except Exception as e:
            print(f"Skipping {f}: {e}")

    if not dfs:
        print("No readable parquet files found.")
        return

    df = pd.concat(dfs, ignore_index=True)

    # Target columns (1d)
    cols = ["recommend_all_1d", "recommend_ma_1d", "recommend_other_1d"]
    # Check if columns exist
    missing = [c for c in cols if c not in df.columns]
    if missing:
        print(f"Missing columns: {missing}")
        return

    subset = df[cols].dropna()

    if subset.empty:
        print("Insufficient data for regression.")
        return

    print(f"Observations: {len(subset)}")
    print("Samples:", subset.head())

    # Correlation
    corr = subset.corr()
    print("\nCorrelation Matrix:")
    print(corr)

    # Regression
    X = subset[["recommend_ma_1d", "recommend_other_1d"]]
    y = subset["recommend_all_1d"]

    if len(subset) < 2:
        print("\nNote: Not enough data for meaningful regression statistics.")
        # We can still run fit to get the coefficients for this single point (exact solution)

    model = LinearRegression(fit_intercept=False)  # Assuming weighted sum without bias
    model.fit(X, y)

    print("\nRegression Coefficients:")
    print(f"Recommend.All = {model.coef_[0]:.4f} * MA + {model.coef_[1]:.4f} * Other")
    print(f"R-squared: {model.score(X, y):.4f}")


if __name__ == "__main__":
    audit_recommend_all()
