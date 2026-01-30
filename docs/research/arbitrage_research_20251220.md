# Research Report: Binance Multi-Quote Arbitrage Exploration

## 1. Executive Summary
This research explores arbitrage opportunities on Binance between pairs with the same base asset but different quote currencies (USDT, USDC, FDUSD, USD). Real-time scanning using TradingView screener snapshots has identified several candidates with spreads exceeding 0.05% before transaction costs.

## 2. Identified High-Priority Candidates
Based on real-time snapshots (2025-12-20), the following pairs show consistent discrepancies:

| Type | Base Asset | Primary Pair | Alternative Pair | Spread (Gross %) | Direction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| SPOT | UNI | BINANCE:UNIUSDT | BINANCE:UNIUSDC | 0.080% | Buy USDC / Sell USDT |
| SPOT | PENGU | BINANCE:PENGUUSDT | BINANCE:PENGUUSDC | 0.054% | Buy USDC / Sell USDT |
| PERP | ZEC | BINANCE:ZECUSDT.P | BINANCE:ZECUSDC.P | 0.049% | Buy USDC / Sell USDT |
| SPOT | SUI | BINANCE:SUIUSDT | BINANCE:SUIUSDC | 0.041% | Buy USDC / Sell USDT |

## 3. Fee Structure & Tradeability Analysis
To determine the **Net Tradeable Spread**, we must account for Binance's multi-tier fee structure.

### Standard Fee Tiers (VIP 0 - Taker)
*   **USDT Pairs:** 0.1% Spot / 0.05% Perp
*   **USDC Pairs:** Often part of "Zero Fee" promotions or 0.1% Spot.
*   **FDUSD Pairs:** Frequently 0% Maker fee, 0.1% Taker.

### Estimated Breakeven Thresholds
*   **Spot-Spot (USDT/USDC):** Combined taker fees ~0.20%. *Current discovered spreads (0.08%) are not yet tradeable for VIP 0.*
*   **Spot-Spot (FDUSD/USDT):** If FDUSD taker is 0% or promoted, breakeven drops to ~0.10%.
*   **Perp-Perp:** Combined taker fees ~0.10%.

## 4. Risks & Technical Constraints
1.  **Stablecoin Pegs:** A spread between `BTCUSDT` and `BTCUSDC` is often just a reflection of the `USDT/USDC` rate. True arbitrage requires a 3-way cycle (Triangular).
2.  **Execution Latency:** TradingView data may have 100ms-500ms latency compared to direct Binance API.
3.  **Liquidity Depth:** Top 50 base assets generally have sufficient depth, but alternative quotes (USDC/FDUSD) often have thinner order books, increasing slippage.

## 5. Next Steps for Tooling
1.  **Triangular Monitoring:** Expand scanner to include `USDT/USDC` and `FDUSD/USDT` stablecoin pairs to detect "True" vs "Peg-Proxy" spreads.
2.  **Slippage Awareness:** Integrate order book depth (Bid/Ask size) to calculate effective spread for institutional volume.
3.  **Cross-Exchange Expansion:** Research Bybit/OKX alternatives for cross-venue arbitrage.
