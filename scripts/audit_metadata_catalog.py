import logging

from tradingview_scraper.symbols.overview import Overview
from tradingview_scraper.symbols.stream.metadata import ExchangeCatalog, MetadataCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audit_metadata")


def audit_catalogs():
    sym_catalog = MetadataCatalog()
    ex_catalog = ExchangeCatalog()

    sym_df = sym_catalog._df
    ex_df = ex_catalog._df

    print("\n" + "=" * 80)
    print("METADATA CATALOG AUDIT")
    print("=" * 80)

    # 1. Exchange Audit
    print(f"\n[1] Exchange Catalog ({len(ex_df)} entries)")
    if ex_df.empty:
        print("  !!! Exchange Catalog is EMPTY")
    else:
        for _, row in ex_df.iterrows():
            print(f"  - {row['exchange']:<10} | TZ: {row['timezone']:<10} | Crypto: {row['is_crypto']}")

    # 2. Symbol Audit - Missing Fields
    print(f"\n[2] Symbol Catalog Coverage ({len(sym_df)} total records, {len(sym_df[sym_df['valid_until'].isna()])} active)")

    active_df = sym_df[sym_df["valid_until"].isna()]

    critical_fields = ["description", "pricescale", "minmov", "tick_size", "timezone"]
    execution_fields = ["lot_size", "contract_size"]

    print("\n  Missing Critical Fields (Active Symbols):")
    for field in critical_fields:
        missing = active_df[active_df[field].isna()]
        pct = (len(missing) / len(active_df)) * 100 if not active_df.empty else 0
        print(f"    - {field:<15} : {len(missing):>3} missing ({pct:>5.1f}%)")

    print("\n  Missing Execution Fields (Gaps for Connector Phase):")
    for field in execution_fields:
        missing = active_df[active_df[field].isna()]
        pct = (len(missing) / len(active_df)) * 100 if not active_df.empty else 0
        print(f"    - {field:<15} : {len(missing):>3} missing ({pct:>5.1f}%)")

    # 3. TV API Discrepancy Check (Sample)
    print("\n[3] TV API Consistency Check (Sample of 3 symbols)")
    ov = Overview()
    sample_symbols = active_df["symbol"].head(3).tolist()

    for symbol in sample_symbols:
        print(f"\n  Checking {symbol}...")
        res = ov.get_symbol_overview(symbol)
        if res["status"] == "success":
            tv_data = res["data"]
            catalog_record = sym_catalog.get_instrument(symbol)

            # Compare key fields
            fields_to_compare = {"pricescale": "pricescale", "minmov": "minmov", "type": "type", "description": "description"}

            for cat_f, tv_f in fields_to_compare.items():
                cat_val = catalog_record.get(cat_f)
                tv_val = tv_data.get(tv_f)

                status = "[MATCH]" if str(cat_val) == str(tv_val) else "[MISMATCH]"
                print(f"    {cat_f:<15} | Catalog: {str(cat_val):<20} | TV: {str(tv_val):<20} {status}")
        else:
            print(f"    !!! Failed to fetch TV data: {res.get('error')}")


if __name__ == "__main__":
    audit_catalogs()
