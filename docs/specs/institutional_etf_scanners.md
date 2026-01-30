# Specification: Institutional ETF Discovery Pipeline

## Overview
The Institutional ETF Discovery Pipeline provides a high-fidelity, cross-asset universe spanning Equities, Bonds, and Commodities. It is designed to emit a stable, institutional-grade basket of assets for hierarchical risk parity (HRP) and barbell allocation.

## Multi-Asset Coverage
The pipeline is composed of nine specialized sub-scanners across three liquidity tiers:

### Layer A: Deterministic Anchors (Static - $10M+ Floor)
1.  **Broad Index ETFs** (`index_etf_trend`): Core market beta (SPY, QQQ, IWM, VTI, etc.).
2.  **Sector Select ETFs** (`sector_etf_trend`): 11 SPDR Select Sectors (XLK, XLF, XLV, etc.).
3.  **Liquid Bond ETFs** (`bond_trend`): Institutional bond anchors (LQD, HYG, TLT, IEF, SHY).
4.  **Commodity ETF Anchors** (`commodity_etf_trend`): Canonical hard assets (GLD, SLV, USO, UNG).

### Layer B: Dynamic Aggressors (Trend-Based - $10M+ Floor)
5.  **Equity Momentum** (`etf_equity_momentum`): Dynamically discovers top-performing growth/thematic ETFs.
6.  **Bond Yield Trend** (`etf_bond_yield_trend`): Identifies emerging trends in specialized fixed income.
7.  **Commodity Supercycle** (`etf_commodity_supercycle`): Captures secular momentum in hard assets.

### Layer C: Niche & Thematic Alpha (Trend-Based - $2M+ Floor)
8.  **Thematic Momentum** (`etf_thematic_momentum`): High-beta, leveraged, and thematic satellites.
    - **Logic**: Sort by **Volume** first (Liquid), then Rank by **1M Perf**.
    - **Attributes**: Includes `aum`, `expense_ratio`, `brand`, `Perf.Y`, `Perf.YTD`, `Volatility.M`.
    - **Thresholds**: Relaxed (`ADX > 15`, `Perf.1M > 0.0`) to capture volatile alpha.
    - **Consolidation**: Now includes Category `71` (Alternative/Crypto) previously targeted by legacy scanners.
9.  **Yield Alpha** (`etf_yield_alpha`): High-yield bonds, Munis, and Dividend strategies.
    - **Logic**: Sort by **Volume** first (Liquid), then Rank by **3M Perf**.
    - **Attributes**: Includes `dividend_yield_recent`, `aum`, `Perf.Y`, `Perf.YTD`, `Volatility.M`.
    - **Thresholds**: Relaxed (`ADX > 10`, `Perf.1M > -1.0`) to capture yield stability.

## Discovery Logic & Sorting
The dynamic discovery engine employs a **"Liquid Winners"** strategy to solve the API starvation problem:

1.  **Phase 1: Fetch (Liquidity Priority)**
    - Sorts the entire API universe by `Value.Traded` (Descending).
    - Fetches the top **300 candidates** matching the `category` filter.
    - *Rationale*: Ensures we do not miss the most tradeable assets just because they aren't the absolute highest performers (which are often illiquid).

2.  **Phase 2: Filter (Quality Gates)**
    - Applies relaxed trend and hygiene filters (e.g., `ADX > 15`, `Perf.1M > 0.0`).
    - Removes duplicate base symbols and stablecoins.

3.  **Phase 3: Rank (Alpha Priority)**
    - Re-sorts the surviving liquid pool by Performance (`Perf.1M`) or Yield (`Perf.3M`).
    - Returns the Top 20 "Liquid Winners".

## Market Categorization (Asset Class Proxy)
Since `asset_type` is not available, we use TradingView `category` IDs to distinguish asset classes:

| ID | Asset Class | Description | Scanner Target |
| :--- | :--- | :--- | :--- |
| `26`, `27` | **Equity** | Broad Market, Thematic, Leveraged | `etf_thematic_momentum` |
| `35` | **Volatility** | VIX Futures, Inverse VIX | `etf_thematic_momentum` |
| `71` | **Alternative** | Crypto, Managed Futures | `etf_thematic_momentum` |
| `61`, `70`, `68`, `59` | **Bond** | Muni, Corp, High Yield, EM Bond | `etf_yield_alpha` |
| `69` | **Credit** | Senior Loans, Floating Rate | `etf_yield_alpha` |
| `44` | **Equity Income** | High Dividend Yield | `etf_yield_alpha` |
| `8`, `6`, `4` | **Commodity** | Precious Metals, Energy, Ag | `etf_commodity_supercycle` |

## Audit & Verification (`passes` Object)
The scanner JSON export includes a `passes` object detailing which gates each asset cleared. This provides full traceability for the "Liquid Winners" logic.

### Structure
```json
"passes": {
  "trend_adx": true,          // Passed ADX threshold (e.g. > 15)
  "trend_momentum": true,     // Passed Perf thresholds (e.g. Perf.1M > 0)
  "trend_recommendation": true, // Passed Rating threshold (e.g. > 0.3)
  "trend_combined": true,     // All Trend gates passed
  "all": true                 // Asset is valid for selection
}
```

### Interpretation
- **`all: true`**: The asset is a valid candidate for the final ranking phase.
- **`trend_adx: false`**: Asset is liquid but "choppy" (failed trend strength).
- **`trend_momentum: false`**: Asset is liquid but "lagging" (failed relative strength).

## Audit Checklist (Jan 2026)
- [x] Pattern Consistency: Layer C correctly overrides liquidity floor to $2M.
- [x] Namespace Integrity: Correct usage of `AMEX:` and `NASDAQ:` for US ETF listings.
- [x] Metadata Completeness: All static emitters explicitly fetch volume and value metrics.
- [x] Multi-Asset Balance: Unified universe covers Equities, Bonds, Commodities, and Thematic Satellites.
- [x] **Category Map Validated**:
    - `27`: Leveraged/Inverse/Niche Equity (High Alpha).
    - `8`: Precious Metals (High Alpha).
    - `71`: Crypto/Bitcoin (High Vol).
    - `44`: Dividend Equity (Yield).
    - `69`: Senior Loans (Yield).


