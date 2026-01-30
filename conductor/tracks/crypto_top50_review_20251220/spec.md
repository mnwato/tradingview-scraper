# Spec: Explore and Review Top50 Crypto CEX Base Universes

## Overview
This research and maintenance track aims to audit and optimize the "top 50" base universe filters for major Crypto Centralized Exchanges (CEX): Binance, OKX, Bybit, and Bitget. The goal is to ensure these filters produce a high-quality, tradable base universe for quantitative strategies, focusing on liquidity, market capitalization, and volatility.

## Objectives
- Audit current base universe filtering logic in `configs/crypto_cex_base_top50_*.yaml`.
- Evaluate if the current filters capture the most tradable assets across Binance, OKX, Bybit, and Bitget (Spot & Perps).
- Propose and implement optimized filtering criteria to improve universe quality.
- Generate a summary report of the findings and the impact of the changes.

## Functional Requirements
- **Configuration Review:** Examine all `crypto_cex_base_top50` YAML files in the `configs/` directory.
- **Liquidity Analysis:** Verify that `Value.Traded` and `volume` filters are sufficient to ensure low slippage for common strategy sizes.
- **Market Cap Validation:** Ensure `market_cap_calc` or `market_cap_basic` filters accurately capture the top-tier assets.
- **Volatility Check:** Review if the resulting universes provide sufficient `Volatility.D` or `ATR` characteristics for active trading strategies.
- **Multi-Exchange Alignment:** Synchronize filtering logic across Binance, OKX, Bybit, and Bitget to ensure consistent universe quality while accounting for exchange-specific liquidity differences.

## Acceptance Criteria
- [ ] Comprehensive review of current `top50` YAML configurations completed.
- [ ] Summary report provided, detailing the strengths and weaknesses of the current filters.
- [ ] Updated YAML configuration files implemented with optimized filters for all target exchanges and instrument types (Spot/Perps).
- [ ] Scanners rerun with new configs to verify the resulting universes meet "tradability" standards.

## Out of Scope
- Modifying the core `Screener` or `Streamer` Python logic (unless a bug is found during the review).
- Implementing new strategies based on these universes.
