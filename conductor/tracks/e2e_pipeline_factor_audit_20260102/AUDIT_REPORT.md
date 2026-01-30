# Audit Report: End-to-End Pipeline Factor Mismatch (2026-01-02)

## 1. Overview
This audit reviews the technical consistency between the **Discovery** stage (Scanners) and the **Natural Selection** stage (SelectionEngineV3_2). 

## 2. Identified Inconsistencies

### 2.1 Momentum Horizon Mismatch
- **Discovery (ETF/Crypto)**: Frequently uses `Perf.3M` (Trailing 3-Month) and `Perf.6M` filters.
- **Natural Selection**: Uses mean returns over the `train_window` (default 126d) and evaluates performance in the `test_window` (default 21d).
- **Impact**: Assets with strong 3-month performance but deteriorating 21-day performance may pass the scanner only to be vetoed by the selector, wasting data backfilling resources.

### 2.2 Volatility Methodology Mismatch
- **Discovery**: Uses `Volatility.D` (Trailing Daily Volatility) and `ATR` (Average True Range).
- **Natural Selection**: Uses window-local standard deviation (σ) and `Antifragility_Score`.
- **Impact**: Early pruning based on `Volatility.D > 35%` might discard high-alpha assets that the Log-MPS engine would have stabilized using hierarchical risk parity.

### 2.3 Liquidity Score Normalization
- **Discovery**: Uses `Value.Traded` with floors ranging from $250k (Crypto) to $20M (ETF).
- **Natural Selection**: `calculate_liquidity_score` uses an institutional baseline of **$500M ADV** ($VT / 5 \times 10^8$).
- **Impact**: Crypto assets passing with $1M ADV receive a selector liquidity score of 0.002, which effectively zeroes out their Log-MPS probability if liquidity is weighted heavily.

## 3. Darwinian Gate Discrepancy (ECI Veto)
- **ECI Logic**: Selector vetoes assets where `Annual Alpha - ECI < eci_hurdle` (0.5%).
- **ECI Components**: Uses `Value.Traded` and window-local volatility.
- **Conflict**: If the scanner hasn't already filtered for high `Value.Traded`, the selector will veto a large percentage of discovered assets after the expensive backfilling process.

## 4. Refactoring Results (Design Alignment)

### 4.1 Layered Configuration Architecture
Implemented a two-layer hierarchy to separate **Tradability** from **Alpha**:
1.  **Layer 1 (Base Presets)**: `base_crypto_spot.yaml`, `base_us_etf.yaml`, `base_binance_spot.yaml`.
    - Handles Volume floors, Volatility caps, and initial market scope.
    - Standardized to $50M ADV for Crypto and $500M ADV for Equities.
2.  **Layer 2 (Strategy Configs)**: `crypto_cex_trend_momentum.yaml`, `us_etf_trend_momentum.yaml`.
    - Inherits from Layer 1.
    - Aligned momentum horizons to `Perf.1M` and `Perf.W` to match 21-day Selector windows.

### 4.2 Pipeline Instrumentation
- **Scoring Logic**: Updated `tradingview_scraper/utils/scoring.py` with market-aware liquidity baselines.
- **Pre-Selection Estimator**: Integrated `eci_pre_veto` into `scripts/enrich_candidates_metadata.py` to prevent wasted backfilling of high-cost assets.

## 5. Conclusion
The pipeline is now mathematically aligned from Discovery to Natural Selection. Factor Drift has been minimized by synchronizing momentum horizons and standardizing liquidity metrics across all stages.
