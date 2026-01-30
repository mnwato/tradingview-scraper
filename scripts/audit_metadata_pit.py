import pandas as pd


def audit_pit_integrity():
    sym_path = "data/lakehouse/symbols.parquet"
    df = pd.read_parquet(sym_path)

    print("\n" + "=" * 80)
    print("PIT INTEGRITY AUDIT")
    print("=" * 80)

    # 1. Uniqueness of Active Records
    print("\n[1] Active Record Uniqueness (valid_until is NULL):")
    active_df = df[df["valid_until"].isna()]
    duplicates = active_df[active_df.duplicated(subset=["symbol"], keep=False)]
    if duplicates.empty:
        print("  - [PASS] No duplicate active records found per symbol.")
    else:
        print(f"  - [FAIL] {len(duplicates['symbol'].unique())} symbols have multiple active records!")
        print(duplicates[["symbol", "valid_from", "updated_at"]])

    # 2. Contiguity Check
    print("\n[2] Temporal Contiguity (valid_until_N == valid_from_N+1):")
    mismatches = 0
    symbols_with_history = df["symbol"].value_counts()[df["symbol"].value_counts() > 1].index

    for symbol in symbols_with_history:
        history = df[df["symbol"] == symbol].sort_values("valid_from")
        for i in range(len(history) - 1):
            until_n = history.iloc[i]["valid_until"]
            from_n1 = history.iloc[i + 1]["valid_from"]
            # allow small epsilon or exact match
            if until_n != from_n1:
                mismatches += 1
                if mismatches <= 5:
                    print(f"    - mismatch for {symbol}: version {i} ends {until_n}, version {i + 1} starts {from_n1}")

    if mismatches == 0:
        print("  - [PASS] All historical versions are perfectly contiguous.")
    else:
        print(f"  - [FAIL] {mismatches} temporal gaps or overlaps found.")

    # 3. Start Time Review
    print("\n[3] Symbol Awareness Epochs (Earliest valid_from):")
    earliest = df.groupby("symbol")["valid_from"].min().sort_values().head(5)
    print(earliest)


if __name__ == "__main__":
    audit_pit_integrity()
