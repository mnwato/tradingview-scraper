# Crypto Liquidity & Quote Review (December 2025)

## 1. Global Liquidity Distribution

Based on an exploration of the Top 500 symbols by `Value.Traded` across Binance, OKX, Bybit, and Bitget.

### Top Quote Currencies by Share
| Quote | Liquidity Share | Context |
|-------|-----------------|---------|
| **USDT** | 86.07% | Primary standard for Linear Perps and Altcoin Spot. |
| **USD**  | 12.86% | Primary standard for Inverse Perps. |
| **OTHER**| 1.02%  | Mostly Dated Futures and Internal stablecoin pairs. |
| **IDR**  | 0.04%  | Local currency noise (Binance). |
| **TRY**  | < 0.01%| Local currency noise (Binance). |

## 2. "Proper Quotes" Definition

To ensure institutional-grade data and avoid local currency inflation artifacts, we restrict our universe selection to the following "Proper Quotes":

- **USDT:** Tether (Linear)
- **USDC:** Circle USD (Linear)
- **USD:** US Dollar (Inverse/Quoted)
- **DAI:** Multi-Collateral Dai
- **BUSD / FDUSD:** Binance-affiliated stablecoins

**Excluded:** All non-USD fiat currencies (`IDR`, `TRY`, `BRL`, `JPY`, `EUR`, `ARS`, `COP`).

## 3. Treatment of Duplicates & Aggregation

When a core asset (e.g., Bitcoin) exists in multiple forms, we apply the following aggregation logic to select a single unique representative for the base universe:

### Normalization
- Strip exchange prefixes (`BINANCE:`)
- Strip perpetual suffixes (`.P`)
- Strip numeric scaling prefixes (`1000PEPE` -> `PEPE`)

### Selection Priority
1. **Quote Rank:** Prefer Linear (`USDT`, `USDC`) over Inverse (`USD`).
2. **Instrument Type:** Prefer Perpetual Contracts over Spot Markets.
3. **Liquidity:** Highest `Value.Traded` is the ultimate tie-breaker.

## 4. Verification Results (Top 50 Base)

The following floor liquidity was observed for the 50th asset in the finalized universes:
- **Binance Spot:** ~$2.2M daily value.
- **Binance Perp:** ~$5.2M daily value.
- **OKX Perp:** ~$1.4M daily value.
- **Bitget Perp:** ~$1.0M daily value.

All selected assets are institutional-grade with significant execution capacity.
