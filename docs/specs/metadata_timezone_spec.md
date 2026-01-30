# Technical Specification: Metadata Timezone, Session & Profile (PIT-Safe)
**Status**: Formalized
**Date**: 2025-12-21 (amended 2025-12-28)

## 1. Overview
Accurate timezone, session, and market-profile metadata is required to:

- Prevent look-ahead bias in backtests (Point-in-Time metadata lookup).
- Prevent survivorship bias (do not overwrite or delete instrument history).
- Ensure gap detection and data health checks are market-aware.
- Ensure execution and reporting respects local market conventions.

This specification defines the authoritative resolution hierarchy for `timezone`, `session`, and `profile`, and mandates that `profile` is persisted as a versioned field.

## 2. Resolution Hierarchy
When a symbol is added or updated in the catalog, its contextual fields are resolved using the following priority.

### A) Timezone
1. **TradingView API (`timezone`)**: If `Overview.get_symbol_overview(..., fields=[...])` returns a valid IANA timezone (e.g., `America/New_York`), it is authoritative.
2. **Canonical Exchange Defaults**: If the API returns `None` (common for Crypto, Forex, Futures), inherit from the exchange’s canonical defaults (`ExchangeCatalog`, bootstrapped from `DEFAULT_EXCHANGE_METADATA`).
3. **Global Fallback**: If neither source provides a value, default to `UTC`.

### B) Session
1. **TradingView API (`session`)**: If present, persist it.
2. **Canonical Defaults**:
   - **Crypto**: `24x7`.
   - **Non-crypto**: inherit from exchange/profile defaults when available.
3. **Global Fallback**: If unknown, persist `Unknown`.

`24x7` is reserved for Crypto. Non-crypto instruments MUST NOT be coerced to `24x7` when the API returns `None`.

### C) Profile (Persisted)
`profile` is a required, versioned field in `symbols.parquet`.

- **Derivation**: derived deterministically from a combination of `exchange`, `type`, and `subtype`.
- **Persistence**: stored in the catalog so that future changes to derivation heuristics do not rewrite history.
- **Usage**: used for market-aware calendars (e.g. weekends/US holidays), gap detection, and backtesting invariants.

## 3. Canonical Exchange Metadata
Authoritative exchange defaults are maintained in `tradingview_scraper/symbols/stream/metadata.py` and materialized in `data/lakehouse/exchanges.parquet`.

## 4. PIT & Survivorship Requirements
The catalog MUST implement a Slowly Changing Dimension (SCD Type 2) model:

- Updates MUST NOT overwrite the active record.
- Old records MUST be retired by setting `valid_until = NOW`.
- New records MUST be inserted with `valid_from = NOW`.
- **Contiguity Guarantee**: The `valid_until` of a retired record MUST match the `valid_from` (or `updated_at`) of the succeeding record to ensure a seamless historical chain without gaps or overlaps.
- Backtests MUST query metadata with `as_of=candle_timestamp`.

Deletion of catalog files is prohibited for production/backtesting workflows because it destroys PIT history and can introduce survivorship/look-ahead bias.

## 5. Verification Procedures
Consistency is enforced via audits (Makefile shortcuts: `make meta-audit-offline`, `make meta-audit`):

- `scripts/audit_metadata_timezones.py`: validates resolution hierarchy invariants.
- `scripts/audit_metadata_pit.py`: validates PIT uniqueness/contiguity.

Minimum invariants:

- **Completeness**: no active symbol may have a null or invalid timezone.
- **Crypto rule**: crypto symbols must resolve to `timezone=UTC` and `session=24x7`.
- **Equity sanity**: equities should resolve to `America/New_York` (or an exchange-appropriate timezone) and MUST NOT be `24x7`.
