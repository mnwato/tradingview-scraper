import pandas as pd

df = pd.read_parquet("data/lakehouse/symbols.parquet")
active = df[df["valid_until"].isna()]
print(f"Total records in file: {len(df)}")
print(f"Active symbol versions: {len(active)}")
print(f"Unique active symbols: {active['symbol'].nunique()}")
print("\nActive symbols per exchange:")
print(active.groupby("exchange")["symbol"].count())
print("\nActive symbols per type:")
print(active.groupby("type")["symbol"].count())
