# Crypto Universe Selection Strategy

This document outlines the logic behind the universe selection presets used in the scanning infrastructure, specifically differentiating between **Volume-based** and **Market Cap-based** universes.

## 1. The Core Conflict: Volume vs. Market Cap

When selecting a "Top 50" universe for trading scans, there are two primary approaches:

### A. Market Cap (The "Blue Chip" Approach)
*   **Definition:** Selects the top 50 assets by total network value.
*   **Characteristics:** Stable, slow-moving, high institutional interest.
*   **Pros:** Filters out "flavor of the week" scams; ensures long-term viability.
*   **Cons:** Misses high-momentum breakout assets that haven't yet reached a high market cap. A high market cap coin can have low volatility and low volume, making it poor for trend trading.
*   **Best For:** Mean Reversion strategies, Portfolio Rebalancing, Index Tracking.

### B. Value Traded (The "Action" Approach)
*   **Definition:** Selects the top 50 assets by 24h USD trading volume (`Value.Traded`).
*   **Characteristics:** High liquidity, high attention, volatile.
*   **Pros:** Captures exactly where the market attention is *right now*. Essential for momentum and trend-following strategies.
*   **Cons:** Can include "garbage" coins (memecoins, pump-and-dumps) that are temporarily popular but fundamentally unsound.
*   **Best For:** Trend Following, Momentum, Breakout strategies.

## 2. Refined Hybrid Strategy (2025-12-20 Update)

To ensure both **Liquidity Priority** and **Institutional Stability**, we have implemented a multi-stage pipeline:

### The "Liquidity Floor + Market Cap Rank" Guard
Instead of choosing between Volume or Market Cap, we now use a dual-layer approach:
1.  **Liquidity Floor:** Every asset must pass a minimum `Value.Traded` ($1M - $5M depending on config) to be considered executable.
2.  **Hybrid Market Cap Guard:**
    *   **Rank Guard:** Only assets in the Top 200 (or 300) of the global market cap (using `market_caps_crypto.json`) are included.
    *   **Floor Guard:** Enforces an absolute minimum market cap ($10M) using the maximum of TradingView's `market_cap_calc` or external data.
3.  **Strict Quote Whitelist:** Only USD-denominated quotes (`USDT`, `USDC`, `USD`, `DAI`, `BUSD`, `FDUSD`) are allowed. This eliminates local fiat noise (IDR, TRY, JPY) that can inflate "Value Traded" rankings.
4.  **Dated Futures:** Delivery contracts are excluded by default (spot/perp scans use `exclude_dated_futures: true`) to reduce expiry noise. Separate `*_dated*` configs intentionally set `include_dated_futures_only: true` (and must not set `exclude_dated_futures: true`).

## 3. Aggregation & Summed Liquidity

Symbols with the same base asset (e.g., `BTCUSDT`, `BTCUSDC`, `BTCUSD.P`, `1000PEPEUSDT.P`) are automatically aggregated into a single entry per base currency.

**Summed Liquidity Scoring:**
The `Value.Traded` and `volume` fields for the representative asset now reflect the **summed total** across all grouped duplicates. This provides an accurate measure of total market depth for the base asset, ensuring major assets are correctly ranked even if their liquidity is fragmented across multiple quotes.

**Selection Priority for the Representative Symbol:**
1.  **Quote Priority:** Prefers `USDT` > `USDC` > `USD` > `DAI` > `BUSD` > `FDUSD` (favoring Linear over Inverse).
2.  **Product Type:** Prefers Perpetual contracts over Spot (if `prefer_perps` is enabled).
3.  **Tie-breaker:** Highest individual `Value.Traded` wins.

**Alternatives Tracking:**
Grouped duplicates are preserved in the `alternates` field, providing downstream strategies with all tradeable pairs for arbitrage or cross-exchange execution. See [Arbitrage Research](research/arbitrage_research_20251220.md) for more details.

## 4. Institutional Standards (Trend Strategy)

As of December 2025, all crypto trend-following strategies follow these standardized "Institutional Grade" limits:
- **Base Universe Width:** Standardized to **Top 50 unique bases** per venue.
- **Liquidity Floors (Summed VT):**
    - **Binance:** $1M (Spot) / $5M (Perp)
    - **Bybit/OKX/Bitget:** $500k (Spot) / $1M (Perp)
- **Dated Futures (spot/perp scans):** Explicitly excluded (`exclude_dated_futures: true`) to avoid illiquid expiry-based noise.
- **Dated Futures (delivery scans):** Use `include_dated_futures_only: true` and `exclude_dated_futures: false`.
- **Market Cap Guard:** Top 200 Rank Guard + $10M Floor Guard.

## 3. Recommendation

**For the current Trend Scanning Suite:**
> **Use the Volume-Based (Generic) Presets.**

**Reasoning:**
The scans identified candidates like `PIPPIN`, `XMR`, and high-volatility moves in `AVAX` and `NEAR`.
*   Some of these were **missing** from the strict Top 50 Market Cap universe because their valuation hadn't caught up to their volume.
*   Restricting a Trend Bot to Market Cap limits its potential to catch early movers.
*   Liquidity (Value Traded) is a sufficient safety filter (e.g., >$5M daily volume) to avoid illiquid traps, making the Market Cap filter redundant for short-term safety.

**Conclusion:**
Keep the `crypto_cex_trend_...` configurations pointing to the generic (Volume-sorted) presets. Use the `top50` presets only for reporting or specific mean-reversion strategies that require high stability.
