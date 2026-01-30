# Specification: Dynamic ETF Discovery (L4)

## 1. Overview
This document defines the requirements and design for expanding the institutional ETF universe using dynamic trend and momentum-based scanners. This complements the existing static anchor discovery by identifying emerging alpha candidates that meet strict institutional liquidity and trend quality gates.

## 2. Requirements

### 2.1 Liquidity Guardrails
All dynamically discovered assets MUST meet the institutional hygiene floor to ensure executable capacity.
- **Physical Type**: `fund` (Covers ETFs and Mutual Funds in the `america` market).
- **Min Daily Turnover**: $10,000,000 USD (`Value.Traded`).
- **Market Cap Floor**: $500,000,000 USD (where applicable for ETF AUM).

### 2.2 Momentum & Trend Quality
To filter out "noisy" or "choppy" assets, discovery logic utilizes multi-horizon momentum and trend strength indicators.
- **Trend Strength**: `ADX(14) > 20` (Equities/Commodities), `ADX(14) > 12` (Bonds).
- **Trend Stability**: `Volatility.D < 4.0` (Daily volatility floor to prevent extreme noise).
- **Moving Average Alignment**: `EMA(20) > EMA(50)` (Bullish alignment).
- **Momentum Horizons**:
    - Short-term: `Perf.W > 0`.
    - Medium-term: `Perf.1M > 1.5%`.
    - Secular: `Perf.3M > 3.0%`.

### 2.3 Asset Class Diversity
The expansion utilizes numeric `category` IDs for robust asset class isolation:
1.  **Equity Aggressors**: Categories `26`, `27`, `44` (Dividend/Quality).
2.  **Bond Yield Rotators**: Categories `61`, `70`, `68`, `59`, `58`, `63`, `62`, `69`, `64`, `56`, `57`.
3.  **Commodity Supercycle**: Categories `8`, `6`, `4`, `7`, `5`.
4.  **Alternative Alpha**: Categories `1`, `3`, `71` (Managed Futures, Balanced, Crypto).



## 3. Design: The "Anchor + Aggressor" Discovery Model

The `institutional_etf` profile will utilize a composite discovery pipeline:

### Layer A: Deterministic Anchors (Static)
- **Role**: Ensures covariance matrix stability and baseline exposure.
- **Assets**: SPY, QQQ, GLD, LQD, BND, etc.
- **Mode**: `static_mode: true`.

### Layer B: Dynamic Aggressors (Trend-Based)
- **Role**: Captures emerging alpha and sector rotation.
- **Mode**: `static_mode: false` (Open-ended search).
- **Limit**: Max 50 additional symbols.

## 4. Implementation Specifications

### 4.1 Base Preset (`configs/base/universes/dynamic_etf_discovery.yaml`)
Inherits from `institutional.yaml` and enforces the $10M liquidity floor for all open-ended searches.

### 4.2 Dynamic Scanners
| Scanner ID | Logic | Target |
| :--- | :--- | :--- |
| `etf_thematic_momentum` | `Value.Traded` First, then `Perf.1M` Rank | Category `26, 27, 35, 71` |
| `etf_yield_alpha` | `Value.Traded` First, then `Perf.3M` Rank | Category `61, 70, 68, 69...` |
| `etf_commodity_supercycle`| `Perf.3M` Rank Top 15 | Category `8, 6, 4...` |

## 5. Validation Plan
1.  **Discovery Audit**: Verify total symbol count across all scanners.
2.  **Grand Tournament**: Compare "Static-Only" vs "Expanded" universes.
3.  **Alpha Isolation**: Measure the specific performance contribution of dynamically discovered assets via the `alpha_isolation.md` report.
4.  **Attribute Verification**: Ensure critical fields (`aum`, `expense_ratio`, `Perf.Y`) are present in export.

## 6. Filter Architecture

The discovery engine employs a **Split-Layer Filtering** strategy to solve the "Liquidity vs Alpha" conflict (API starvation):

### Layer 1: API Coarse Filter (Pre-Fetch)
**Role**: Efficiently narrow the universe to a tradeable subset within a target category.
- **Config**: `filters: [...]` in YAML.
- **Key Fields**: `category` (Asset Class), `Value.Traded` (Liquidity Floor).
- **Execution**: Passed directly to `scanner.tradingview.com`.
- **Limit**: Controlled by `prefilter_limit` (e.g., 300).
- **Sorting**: `Value.Traded` (Descending) - Ensures we get the most liquid assets first.

### Layer 2: Client Fine Filter (Post-Fetch)
**Role**: Apply strict alpha, trend, and hygiene gates to the liquid candidates.
- **Config**: `trend: { ... }` in YAML.
- **Key Fields**: `ADX` (Trend Strength), `Perf.1M` (Momentum), `Volatility.D` (Risk).
- **Execution**: Processed in `FuturesUniverseSelector.process_data()`.
- **Output**: Generates the `passes` object in the JSON export.

### Layer 3: Ranking (Final Selection)
**Role**: Prioritize the survivors based on the primary alpha signal.
- **Config**: `final_sort_by` in YAML.
- **Key Fields**: `Perf.1M` (Thematic), `Perf.3M` (Yield).
- **Execution**: Re-sorts the filtered list before truncating to `limit` (e.g., 20).
4.  **Attribute Verification**: Ensure critical fields (`aum`, `expense_ratio`, `Perf.Y`) are present in export.
