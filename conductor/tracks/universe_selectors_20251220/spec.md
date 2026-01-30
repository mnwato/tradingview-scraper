# Spec: Review and Update Universe Selectors

## Overview
This maintenance track focuses on reviewing and updating the selection and filtering logic across the library's universe selectors. This ensures that the universes (Crypto, US Equities, Forex, and Futures) are accurately defined and filtered based on relevant criteria like market cap, volume, and sector.

## Objectives
- Enhance the selection logic for Crypto (Spot/Perps), US Stocks/ETFs, and Forex/Futures.
- Align filtering criteria with current quantitative trading standards.
- Improve the flexibility and maintainability of the universe definition process.

## Functional Requirements
- **Logic Review:** Audit the existing selection logic in `tradingview_scraper/cfd_universe_selector.py` and `tradingview_scraper/futures_universe_selector.py`.
- **Criteria Update:** Update or refine filtering parameters (e.g., market cap thresholds, volume requirements, exchange filtering) within both the Python modules and the YAML configuration files in `configs/`.
- **Multi-Market Consistency:** Ensure consistent application of selection rules where appropriate across different asset classes.
- **Config Synchronization:** Verify that the library correctly parses and applies the updated YAML configurations.

## Non-Functional Requirements
- **Efficiency:** The universe selection process should be performant and not introduce significant latency.
- **Documentation:** Clear documentation of the selection criteria for each universe.

## Acceptance Criteria
- [ ] Updated selection logic is implemented in the relevant Python modules.
- [ ] YAML configuration files in `configs/` reflect the new selection criteria.
- [ ] Universe selectors correctly filter and return the expected sets of symbols for all focused markets.
- [ ] No regressions are introduced in the core scraping or streaming functionality.
