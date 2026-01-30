Strategies & Setups
===================

This document outlines specific trading strategies and setups identified within the universe selector framework.

Confirmed Short Setup (Bearish)
-------------------------------
The "Confirmed Short" setup identifies assets that are in a verified downtrend but may be experiencing a short-term counter-trend bounce. This serves as a high-quality watchlist for potential short entries when the bounce fades.

**Definition:**

1.  **Trend Confirmation:**
    *   **Recommendation:** Sell or Strong Sell (``Recommend.All <= -0.2``).
    *   **Negative Momentum:** Significant price decline over the medium term (e.g., ``Perf.1M <= -0.5%`` AND ``Perf.3M <= -1.0%``).
    *   **ADX:** Trend strength validation (``ADX >= 10``).

2.  **Execution Filter (Ignored for Watchlist):**
    *   Normally, the execution logic requires the **Daily Change** to be negative (e.g., ``< 0.2%``) to confirm the downtrend is active.
    *   For the "Confirmed Setup" watchlist, we **ignore** the daily change. This allows us to spot assets that are fundamentally bearish but are currently "green" (bouncing), which often presents better risk/reward ratios for short entries than chasing a dump.

**Usage:**

- **Scan:** Run a "short" trend scan but look for assets rejected *only* by the execution (Daily Change) filter.
- **Action:** Add to watchlist. Wait for the daily candle to turn red or for intraday breakdown signs before entering.

**Example Candidates (as of Dec 2025):**

- BTCUSD.P, ETHUSD.P, SOLUSDT.P, XRPUSDT.P, DOGEUSDT.P
- These assets showed strong negative 1M/3M performance and Sell ratings but were rejected by daily trend filters during market bounces.

Binance Top 50 Universe
-----------------------
A standardized, high-quality universe for strategy development on Binance.

**Perpetual Futures (`binance_top50_perp_base`)**

- **Criteria:** Top 50 assets by **Value Traded** (24h Volume * Price).
- **Filters:**
    - Minimum Daily Value Traded: $15,000,000
    - Max Daily Volatility: 15%
- **Goal:** Ensures strategies run only on the most liquid instruments where execution slippage is minimized.

**Spot (`binance_top50_spot_base`)**

- **Criteria:** Top 50 assets by **Market Capitalization**.
- **Filters:**
    - Minimum Daily Value Traded: $5,000,000
    - Max Daily Volatility: 15%
- **Goal:** Focuses on established, high-cap assets for longer-term holding or spot swing trading.
