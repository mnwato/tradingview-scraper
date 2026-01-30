#!/usr/bin/env python3
"""
Comprehensive audit script for exchange and symbol catalogs.
Avoids pandas complexity by using basic Python data structures.
"""

import logging
from typing import cast

import pandas as pd

from tradingview_scraper.symbols.stream.metadata import DEFAULT_EXCHANGE_METADATA, ExchangeCatalog, MetadataCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comprehensive_audit")


def comprehensive_exchange_symbol_audit():
    """
    Performs comprehensive audit of exchange and symbol catalogs.
    """
    logger.info("Starting comprehensive exchange and symbol audit...")

    # Load catalogs
    sym_catalog = MetadataCatalog()
    ex_catalog = ExchangeCatalog()

    df = sym_catalog._df
    ex_df = ex_catalog._df

    print("\n" + "=" * 80)
    print("COMPREHENSIVE EXCHANGE & SYMBOL CATALOG AUDIT")
    print("=" * 80)

    # Exchange catalog audit
    print("\n[EXCHANGE CATALOG ANALYSIS]")
    print(f"Total exchanges: {len(ex_df)}")

    # Exchange coverage analysis
    active_df = cast(pd.DataFrame, df[df["valid_until"].isna()])

    print("\n--- Exchange Coverage ---")
    exchange_counts = cast(pd.Series, active_df["exchange"]).value_counts()
    for exchange, count in exchange_counts.items():
        print(f"{exchange:<15}: {count:>3} symbols")

    # Exchange consistency with defaults
    print("\n--- Default Metadata Coverage ---")
    missing_exchanges = []
    inconsistent_exchanges = []

    for ex_name, defaults in DEFAULT_EXCHANGE_METADATA.items():
        ex_record = ex_catalog.get_exchange(ex_name)
        if not ex_record:
            missing_exchanges.append(ex_name)
            continue

        issues = []
        if ex_record["timezone"] != defaults["timezone"]:
            issues.append(f"TZ: {ex_record['timezone']} vs {defaults['timezone']}")
        if ex_record["is_crypto"] != defaults["is_crypto"]:
            issues.append(f"Crypto: {ex_record['is_crypto']} vs {defaults['is_crypto']}")
        if ex_record["country"] != defaults["country"]:
            issues.append(f"Country: {ex_record['country']} vs {defaults['country']}")

        if issues:
            inconsistent_exchanges.append(f"{ex_name}: {', '.join(issues)}")
        else:
            print(f"✓ {ex_name:<15}: Consistent")

    if missing_exchanges:
        print(f"\n⚠ Missing exchanges: {', '.join(missing_exchanges)}")

    if inconsistent_exchanges:
        print("\n⚠ Inconsistent exchanges:")
        for issue in inconsistent_exchanges:
            print(f"  {issue}")

    # Symbol catalog audit
    print("\n[SYMBOL CATALOG ANALYSIS]")
    print(f"Total records: {len(df)}")
    print(f"Active symbols: {len(active_df)}")

    # Field completeness
    print("\n--- Field Completeness ---")
    critical_fields = ["description", "pricescale", "minmov", "tick_size", "timezone", "session"]
    for field in critical_fields:
        missing = active_df[field].isna().sum()
        pct = (missing / len(active_df)) * 100 if len(active_df) > 0 else 0
        print(f"{field:<15}: {missing:>3} missing ({pct:>5.1f}%)")

    # Exchange distribution for symbol types
    print("\n--- Symbol Type by Exchange ---")
    type_by_exchange = {}
    for exchange in cast(pd.Series, active_df["exchange"]).dropna().unique():
        ex_symbols = active_df[active_df["exchange"] == exchange]
        type_counts = cast(pd.Series, ex_symbols["type"]).value_counts().to_dict()
        type_by_exchange[exchange] = type_counts

    for exchange, types in sorted(type_by_exchange.items()):
        print(f"{exchange:<15}:")
        for symbol_type, count in types.items():
            print(f"  {symbol_type:<10}: {count:>3}")

    # Data quality issues
    print("\n--- Data Quality Issues ---")

    # Orphaned records
    orphaned = active_df[active_df["exchange"].isna()]
    print(f"Orphaned symbols (no exchange): {len(orphaned)}")

    # Invalid symbol formats
    # Allow alphanumeric, colon, underscore, dot (for .P/.F suffixes), and exclamation (for continuous contracts)
    invalid_format = active_df[~active_df["symbol"].str.match(r"^[A-Z_0-9]+:[A-Z0-9_\.!]+$")]
    print(f"Invalid symbol format: {len(invalid_format)}")

    # Type-session consistency
    print("\n--- Type-Session Consistency ---")
    crypto_exchanges = ["BINANCE", "BYBIT", "OKX", "BITGET"]

    session_issues = 0
    for exchange in crypto_exchanges:
        ex_symbols = active_df[active_df["exchange"] == exchange]
        non_24x7 = ex_symbols[~cast(pd.Series, ex_symbols["session"]).fillna("Unknown").eq("24x7")]
        session_issues += len(non_24x7)

    print(f"Crypto exchange session issues: {session_issues}")

    # Timezone analysis
    print("\n--- Timezone Distribution ---")
    tz_counts = cast(pd.Series, active_df["timezone"]).value_counts()
    for tz, count in tz_counts.items():
        print(f"{tz:<25}: {count:>3} symbols")

    # Duplicate analysis
    print("\n--- Duplicate Analysis ---")
    symbol_counts = cast(pd.Series, df["symbol"]).value_counts()
    duplicates = symbol_counts[symbol_counts > 1]

    active_symbol_counts = cast(pd.Series, active_df["symbol"]).value_counts()
    active_duplicates = active_symbol_counts[active_symbol_counts > 1]

    print(f"Symbols with history (duplicates): {len(duplicates)}")
    print(f"Symbols with multiple ACTIVE records: {len(active_duplicates)}")

    if len(active_duplicates) > 0:
        print("⚠ WARNING: Active duplicates detected!")
        for symbol, count in active_duplicates.items():
            print(f"  {symbol}: {count} active versions")

    if len(duplicates) > 0:
        print("Top duplicated symbols:")
        top_duplicates = cast(pd.Series, cast(pd.Series, duplicates).sort_values(ascending=False)).head(10)
        for symbol, count in top_duplicates.items():
            print(f"  {symbol}: {count} versions")

    # Summary statistics
    print("\n--- Summary Statistics ---")
    print(f"Data Quality Score: {calculate_quality_score(active_df):.1f}/100")
    print(f"Coverage Score: {calculate_coverage_score(active_df):.1f}/100")

    return {
        "total_records": len(df),
        "active_records": len(active_df),
        "exchanges_count": len(ex_df),
        "missing_exchanges": missing_exchanges,
        "inconsistent_exchanges": inconsistent_exchanges,
        "orphaned_symbols": len(orphaned),
        "invalid_format_symbols": len(invalid_format),
        "duplicates_count": len(duplicates),
        "quality_score": calculate_quality_score(active_df),
        "coverage_score": calculate_coverage_score(active_df),
    }


def calculate_quality_score(df):
    """Calculate overall data quality score (0-100)."""
    if df.empty:
        return 0

    active_df = df[df["valid_until"].isna()]

    # Factors affecting quality
    total_fields = ["symbol", "exchange", "type", "description", "pricescale", "minmov", "timezone", "session"]
    missing_fields = sum(active_df[field].isna().sum() for field in total_fields)

    # Calculate quality based on completeness
    total_possible = len(active_df) * len(total_fields)
    quality_score = max(0, ((total_possible - missing_fields) / total_possible) * 100)

    return quality_score


def calculate_coverage_score(df):
    """Calculate coverage score based on exchange and type diversity."""
    if df.empty:
        return 0

    active_df = df[df["valid_until"].isna()]

    # Exchange diversity (max 50 points)
    exchange_count = len(active_df["exchange"].dropna().unique())
    exchange_score = min(50, exchange_count * 10)

    # Type diversity (max 50 points)
    type_count = len(active_df["type"].dropna().unique())
    type_score = min(50, type_count * 10)

    # Overall coverage
    coverage_score = exchange_score + type_score

    return coverage_score


if __name__ == "__main__":
    results = comprehensive_exchange_symbol_audit()

    # Generate recommendations
    print("\n--- RECOMMENDATIONS ---")

    if results["missing_exchanges"]:
        print("1. ADD MISSING EXCHANGES:")
        print(f"   Add metadata for: {', '.join(results['missing_exchanges'])}")

    if results["inconsistent_exchanges"]:
        print("\n2. FIX INCONSISTENCIES:")
        print("   Review and standardize exchange metadata")

    if results["orphaned_symbols"] > 0:
        print("\n3. CLEAN ORPHANED SYMBOLS:")
        print(f"   {results['orphaned_symbols']} symbols need exchange assignment")

    if results["invalid_format_symbols"] > 0:
        print("\n4. STANDARDIZE SYMBOL FORMATS:")
        print("   Ensure all symbols follow EXCHANGE:SYMBOL pattern")

    if results["duplicates_count"] > 0:
        # In SCD Type 2, duplicates (history) are fine, only active duplicates are bad
        # We check quality_score for other things
        pass

    if results["quality_score"] < 90:
        print("\n6. IMPROVE DATA QUALITY:")
        print("   Focus on missing critical fields and validation")

    print("\n--- FINAL SCORES ---")
    print(f"Data Quality Score: {results['quality_score']:.1f}/100")
    print(f"Coverage Score: {results['coverage_score']:.1f}/100")
