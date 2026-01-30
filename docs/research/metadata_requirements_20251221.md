# Research Report: Metadata Requirements & Availability
**Date:** 2025-12-21
**Author:** Jules

## 1. Objective
Determine the availability of structural and execution metadata from the primary source (TradingView Scanner API) and identify gaps that require alternative data sources for the Data Lakehouse.

## 2. Findings from TradingView Scanner API

Testing with `scripts/research_metadata_fields.py` against `BINANCE:BTCUSDT` and `BINANCE:BTCUSD.P` revealed the following:

### Available Fields
| Field | Example (BTCUSDT) | Example (BTCUSD.P) | Description |
|-------|-------------------|--------------------|-------------|
| `pricescale` | `100` | `10` | Inverse of tick size (e.g. 100 -> 0.01). Critical for storage & display. |
| `minmov` | `1` | `1` | Minimum movement steps. Tick Size = `minmov` / `pricescale`. |
| `currency` | `USDT` | `USD` | The quote currency or settlement currency. |
| `base_currency`| `BTC` | `BTC` | The underlying asset. **Crucial for symbol parsing.** |
| `type` | `spot` | `swap` | Instrument type. |
| `subtype` | `crypto` | `crypto` | Asset class. |
| `description` | `Bitcoin / TetherUS` | `BTC Perpetual...` | Human readable name. |

### Missing / Unavailable Fields (Gap Analysis)
The following fields returned `None` or are known to be missing:

- **Execution Limits**: `volume_precision`, `lot_size`, `min_order_qty`, `max_order_qty`.
- **Fees**: `maker_fee`, `taker_fee`.
- **Derivatives Specifics**:
    - `expiration` / `expire_date` (for Dated Futures).
    - `pointvalue` / `contract_size` (Multiplier).
    - `settlement_type` (Linear vs Inverse - though `currency` hints at this).

## 3. Lakehouse Metadata Schema Requirements

To support a robust quantitative research and trading environment (simulating execution), the Metadata Service must provide:

### A. Descriptive (Source: TradingView)
- `symbol` (e.g., `BINANCE:BTCUSDT`)
- `base_asset` (`BTC`)
- `quote_asset` (`USDT`)
- `sector` / `industry`

### B. Structural (Source: TradingView)
- `price_precision` (derived from `pricescale`)
- `tick_size` (derived from `minmov`/`pricescale`)

### C. Execution (Source: Exchange API / Manual Config)
- `quantity_precision` / `lot_size` (e.g., 0.001 BTC)
- `min_notional` (e.g., 5 USDT)
- `contract_size` (e.g., 100 USD for inverse perp, or 1 BTC for linear)
- `status` (Trading / Halt)

## 4. Recommendations for Metadata Service

1.  **Hybrid Sourcing**: 
    - Use **TradingView** for the broad universe discovery and basic classification.
    - Use **CCXT** (or direct Exchange API) to enrich the catalog with execution details (`lot_size`, `contract_size`).
    
2.  **Storage**:
    - `symbols.parquet` is sufficient for a minimal V1 prototype, but PIT-safe backtesting requires persisted `profile` and SCD Type 2 fields.
    - Recommended artifacts:
        - `data/lakehouse/symbols.parquet` (symbol metadata, PIT versioned)
        - `data/lakehouse/exchanges.parquet` (exchange defaults for timezone/session/country when the API returns `None`)
    - Minimum schema (symbols): `symbol` (PK), `exchange`, `type`, `subtype`, `base`, `quote`, `pricescale`, `minmov`, `tick_size`, `timezone`, `session`, `profile`, `active`, `valid_from`, `valid_until`, `updated_at`.

3.  **Next Steps**:
    - Prototype a "Metadata Enricher" that takes the TradingView list and queries Binance/Okx/Bybit via REST API to fill gaps.
    - Build on existing catalogs using SCD Type 2 upserts (avoid deletes) so PIT history remains intact for survivorship-safe backtests.
