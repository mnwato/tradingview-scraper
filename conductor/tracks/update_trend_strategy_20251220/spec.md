# Specification: Update Trend Following Strategy Universe Selectors

## Overview
Align the 34+ crypto trend-following strategy configurations with the newly optimized institutional-grade base universe selectors. This ensures that strategy scanners operate on high-liquidity, unique base assets with accurate summed volume metrics and strict market cap guards.

## Functional Requirements
1.  **Inherit Base Logic:** Update all trend-following YAML presets to include:
    *   `dedupe_by_symbol: true`
    *   `group_duplicates: true`
    *   `Value.Traded` summed aggregation logic.
2.  **Standardize Limits:** Expand the final `limit` for all trend strategy scanners to **50 unique bases** to match the base universe width.
3.  **Exclude Dated Futures:** Ensure `exclude_dated_futures: true` is enforced across all trend presets to avoid illiquid expiry-based assets.
4.  **Tuned Liquidity Floors:** Apply the exchange-specific floors identified in the audit:
    *   Binance: $1M VT
    *   Bybit/OKX/Bitget: $500k VT
5.  **Execution:** Run the full suite of crypto trend-following scanners using the updated configurations and verify output quality.

## Acceptance Criteria
- [ ] 100% of trend strategy presets updated with new aggregation and limit settings.
- [ ] No dated futures present in the final strategy outputs.
- [ ] Total `Value.Traded` in strategy results reflects the summed volume across aggregated pairs.
- [ ] Quality verification script passes for the new strategy outputs.

## Out of Scope
- Modification of the underlying trend-following indicators or entry/exit logic.
- Creation of specific strategies for dated futures.
