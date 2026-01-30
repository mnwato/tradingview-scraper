# Plan: Review and Update Universe Selectors

This plan outlines the steps to audit and enhance the universe selection logic for Crypto, US Equities, Forex, and Futures markets.

## Phase 1: Analysis & Research
- [x] Task: Audit `tradingview_scraper/cfd_universe_selector.py` selection logic
- [x] Task: Audit `tradingview_scraper/futures_universe_selector.py` selection logic
- [~] Task: Review YAML files in `configs/` for outdated filtering criteria
- [ ] Task: Conductor - User Manual Verification 'Analysis & Research' (Protocol in workflow.md)

## Phase 2: Implementation - Python Logic (TDD)
- [ ] Task: TDD - Write tests for updated CFD selection filtering (market cap, volume)
- [ ] Task: TDD - Update selection logic in `tradingview_scraper/cfd_universe_selector.py`
- [ ] Task: TDD - Write tests for updated Futures selection filtering
- [ ] Task: TDD - Update selection logic in `tradingview_scraper/futures_universe_selector.py`
- [ ] Task: Conductor - User Manual Verification 'Implementation - Python Logic' (Protocol in workflow.md)

## Phase 3: Configuration & Integration (TDD)
- [ ] Task: TDD - Write tests verifying parsing of updated YAML configs
- [ ] Task: Update filtering parameters in `configs/*.yaml` for focused markets
- [ ] Task: TDD - Verify end-to-end universe selection with new configs
- [ ] Task: Conductor - User Manual Verification 'Configuration & Integration' (Protocol in workflow.md)

## Phase 4: Finalization & Documentation
- [ ] Task: Update documentation (e.g., `docs/universe_selection_strategy.md`) with new criteria
- [ ] Task: Final project-wide linting and type checking (`ruff`, `mypy` if applicable)
- [ ] Task: Conductor - User Manual Verification 'Finalization & Documentation' (Protocol in workflow.md)
