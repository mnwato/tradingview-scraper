import pandas as pd


def explore_catalogs():
    sym_path = "data/lakehouse/symbols.parquet"
    ex_path = "data/lakehouse/exchanges.parquet"

    sym_df = pd.read_parquet(sym_path)
    ex_df = pd.read_parquet(ex_path)

    print("\n" + "=" * 80)
    print("CATALOG EXPLORATION REPORT")
    print("=" * 80)

    # 1. Exchange Catalog Review
    print("\n[1] Exchange Catalog Contents:")
    print(ex_df.to_string(index=False))

    # 2. Symbol Catalog - High Level Stats
    active_df = sym_df[sym_df["valid_until"].isna()]
    print("\n[2] Symbol Catalog Stats:")
    print(f"  - Total Record Count: {len(sym_df)}")
    print(f"  - Active Symbol Count: {len(active_df)}")

    # 3. Field Integrity (Nulls)
    print("\n[3] Null Value Analysis (Active Symbols):")
    null_counts = active_df.isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            pct = (count / len(active_df)) * 100
            print(f"  - {col:<15}: {count:>3} nulls ({pct:>5.1f}%)")

    # 4. Precision & Scale Review
    print("\n[4] Precision & Scale Sample (Smallest Tick Sizes):")
    print(active_df.sort_values("tick_size").head(5)[["symbol", "tick_size", "pricescale", "minmov"]].to_string(index=False))

    print("\n[4b] Precision & Scale Sample (Largest Tick Sizes):")
    print(active_df.sort_values("tick_size", ascending=False).head(5)[["symbol", "tick_size", "pricescale", "minmov"]].to_string(index=False))

    # 5. PIT Versioning Check
    print("\n[5] PIT Versioning Audit (Symbols with History):")
    counts = sym_df["symbol"].value_counts()
    multi_version = counts[counts > 1]
    if multi_version.empty:
        print("  - No symbols with multiple versions found.")
    else:
        print(f"  - Symbols with multiple versions: {len(multi_version)}")
        sample_sym = multi_version.index[0]
        print(f"\n  Version History for {sample_sym}:")
        history = sym_df[sym_df["symbol"] == sample_sym].sort_values("valid_from")
        print(history[["valid_from", "valid_until", "active", "pricescale", "updated_at"]].to_string(index=False))

    # 6. Random Sample for Review
    print("\n[6] Random Sample of 5 Active Symbols:")
    sample = active_df.sample(min(5, len(active_df)))
    for _, row in sample.iterrows():
        print(f"\n--- {row['symbol']} ---")
        for col in row.index:
            if not pd.isna(row[col]):
                print(f"  {col:<15}: {row[col]}")


if __name__ == "__main__":
    explore_catalogs()
