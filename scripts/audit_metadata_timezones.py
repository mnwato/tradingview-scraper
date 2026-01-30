import pandas as pd


def audit_timezones():
    sym_path = "data/lakehouse/symbols.parquet"
    ex_path = "data/lakehouse/exchanges.parquet"

    sym_df = pd.read_parquet(sym_path)
    ex_df = pd.read_parquet(ex_path)
    active_syms = sym_df[sym_df["valid_until"].isna()]

    print("\n" + "=" * 80)
    print("SYSTEMATIC TIMEZONE AUDIT")
    print("=" * 80)

    # 1. Exchange Catalog Audit
    print(f"\n[1] Exchange Timezones ({len(ex_df)} exchanges):")
    for _, row in ex_df.iterrows():
        print(f"  - {row['exchange']:<15}: {row['timezone']}")

    # 2. Symbol Consistency Audit
    print("\n[2] Symbol Consistency Check:")

    # Rule A: All Crypto types should be UTC (standard convention)
    crypto_non_utc = active_syms[(active_syms["subtype"] == "crypto") & (active_syms["timezone"] != "UTC")]
    if crypto_non_utc.empty:
        print("  - [PASS] All Crypto symbols are UTC.")
    else:
        print(f"  - [FAIL] {len(crypto_non_utc)} Crypto symbols are NOT UTC.")
        print(crypto_non_utc[["symbol", "timezone"]].head())

    # Rule B: Check for 'Unknown' or Null timezones
    missing_tz = active_syms[active_syms["timezone"].isna() | (active_syms["timezone"] == "Unknown")]
    if missing_tz.empty:
        print("  - [PASS] No symbols with missing or 'Unknown' timezones.")
    else:
        print(f"  - [FAIL] {len(missing_tz)} symbols have missing timezones.")
        print(missing_tz[["symbol", "exchange", "timezone"]])

    # 3. Exchange Default Inheritance Audit
    # Verify that symbols correctly inherited their exchange's canonical timezone
    print("\n[3] Inheritance Audit (Symbol vs Exchange Catalog):")
    merged = active_syms.merge(ex_df[["exchange", "timezone"]], on="exchange", suffixes=("", "_ex"))
    mismatches = merged[merged["timezone"] != merged["timezone_ex"]]

    if mismatches.empty:
        print("  - [PASS] All symbols match their exchange's canonical timezone.")
    else:
        # Some might be valid overrides from the TV API
        print(f"  - [INFO] {len(mismatches)} symbols differ from exchange defaults (likely API overrides).")
        print(mismatches[["symbol", "timezone", "timezone_ex"]].head(5))


if __name__ == "__main__":
    audit_timezones()
