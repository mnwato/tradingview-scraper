# Plan: Improve Base Universe Selector with Hybrid Market Cap Guard

This plan outlines the steps to refactor the universe selector to enforce dual-layer market cap guards (Rank-based and Floor-based) while maintaining liquidity as the primary filter.

## Phase 1: Logic Refactor (TDD) [checkpoint: e1c122c]
- [x] Task: TDD - Create `tests/test_universe_selector_guards.py` with failing tests for rank and floor guards
- [x] Task: Update `SelectorConfig` in `tradingview_scraper/futures_universe_selector.py` with `market_cap_rank_limit` and `market_cap_floor`
- [x] Task: Implement hybrid guard logic in `FuturesUniverseSelector._apply_market_cap_filter`
- [x] Task: Verify that `Value.Traded` remains the primary sorting and limiting factor
- [x] Task: Conductor - User Manual Verification 'Logic Refactor' (Protocol in workflow.md)
- [x] Task: Refactor `FuturesUniverseSelector.run` to implement an explicit processing pipeline:
    - [x] Task: Implement `_apply_basic_filters` (Exchange, type, stable exclusion)
    - [x] Task: Implement `_aggregate_by_base` (BTCUSDT vs BTCUSDC selection)
    - [x] Task: Re-order `run()` method to: Basic -> Market Cap -> Volatility -> Liquidity -> Aggregation -> Limiting
- [x] Task: TDD - Add test case for BTCUSDT/BTCUSDC aggregation in `tests/test_universe_selector_guards.py`

## Phase 2: Configuration & Integration [checkpoint: 50d9054]
- [x] Task: Update `configs/presets/*.yaml` with the new hybrid guard parameters (e.g., Rank < 200, Floor > $10M)
- [x] Task: Update exchange-specific `configs/crypto_cex_base_top50_*.yaml` files
- [x] Task: Rerun `scripts/run_base_scans.sh` to generate new universes
- [~] Task: Conductor - User Manual Verification 'Configuration & Integration' (Protocol in workflow.md)

## Phase 3: Verification & Reporting [checkpoint: 16a45a5]
- [x] Task: Update `scripts/verify_universe_quality.py` to check for both liquidity floor and market cap guards
- [x] Task: Generate a final report showing the quality and consistency of the selected universes
- [x] Task: Synchronize project-level documentation (`product.md`, `tech-stack.md`)
- [x] Task: Update all YAML configurations with strict quote whitelists and dated futures exclusions
- [x] Task: Update `docs/universe_selection_strategy.md` with the finalized aggregation and filtering logic
