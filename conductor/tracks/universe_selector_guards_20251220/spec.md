# Spec: Improve Base Universe Selector with Hybrid Market Cap Guard

## Overview
This track aims to refine the `FuturesUniverseSelector` to prioritize liquidity (`Value.Traded`) while enforcing a strict "Market Cap Guard." This hybrid guard will use an external file for rank-based filtering (Top N) and real-time screener data for an absolute market cap floor, ensuring the resulting universe consists only of high-quality, high-capacity assets.

## Objectives
- Implement a dual-layer Market Cap Guard:
    - **Guard A (Rank-based):** Only include symbols that appear in the Top N (e.g., Top 200) of the external `market_caps_crypto.json`.
    - **Guard B (Floor-based):** Enforce an absolute minimum market cap (e.g., > $500M) using real-time `market_cap_calc` from TradingView.
- Maintain `Value.Traded` as the primary importance filter for liquidity.
- Improve the `FuturesUniverseSelector` logic to handle this hybrid guard efficiently.
- Verify that the resulting base universes meet both liquidity and market cap quality standards.

## Functional Requirements
- **Selector Refactor:** Update `FuturesUniverseSelector` to implement an explicit pipeline:
    1.  **Basic Filters:** Exchange, symbol, and instrument type (Perp/Dated) filtering.
    2.  **Market Cap Guard:** Apply Rank-based (Top N from file) and Floor-based ($ minimum) guards.
    3.  **Volatility Filter:** Enforce standard volatility and ATR-based bounds.
    4.  **Liquidity Filter:** Enforce `Value.Traded` minimums.
    5.  **Aggregation:** Deduplicate symbols by base currency (e.g., pick most liquid between BTCUSDT and BTCUSDC) *before* limiting the universe.
    6.  **Universe Limiting:** Sort by `Value.Traded` and apply `base_universe_limit` or `limit`.
- **Strict Quote Whitelist:** Limit "Base" universes to institutional-grade quotes: `["USDT", "USDC", "USD", "DAI", "BUSD", "FDUSD"]`. This eliminates local fiat noise (IDR, TRY, ARS, etc.).
- **Dated Futures Exclusion:** Explicitly exclude dated delivery contracts from base universes to focus on tradeable perpetuals and spot.
- **Config Updates:** Ensure YAML configs specify appropriate `market_cap_rank_limit` and `market_cap_floor`.

## Acceptance Criteria
- [ ] `FuturesUniverseSelector` correctly implements the Hybrid Market Cap Guard.
- [ ] Base universes generated only contain assets within the specified Top N rank AND above the dollar floor.
- [ ] Final universe is sorted and limited based on the existing liquidity (`Value.Traded`) and count rules.
- [ ] Verification report shows assets meet both Guard A and Guard B criteria across all exchanges.
