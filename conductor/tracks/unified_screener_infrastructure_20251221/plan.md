# Implementation Plan: Unified Screener Infrastructure
**Track ID**: `unified_screener_infrastructure_20251221`
**Status**: Planned

## 1. Objective
Unify the fragmented screening logic into a single, robust infrastructure that supports both synchronous and asynchronous operations with 100% feature parity.

## 2. Phases

### Phase 1: Architecture Review & Alignment
Goal: Identify implementation overlap and define the unified interface.
- [ ] Task: Audit `screener.py` vs `screener_async.py` for market and column logic gaps.
- [ ] Task: Define the `BaseScreener` interface.

### Phase 2: Unified Core Implementation
Goal: Consolidate shared logic and response formatting.
- [ ] Task: Implement `tradingview_scraper/symbols/screener_base.py` with shared constants and response formatting.
- [ ] Task: Implement the unified `Screener` class supporting `screen()`, `ascreen()`, and `ascreen_many()`.

### Phase 3: Integration & Migration
Goal: Move the codebase to the unified interface.
- [ ] Task: Update `FuturesUniverseSelector` to utilize the unified `Screener`.
- [ ] Task: Update `Overview` and `Pipeline` dependencies.

### Phase 4: Validation & Cleanup
- [ ] Task: Migration verification: Run existing test suites (`test_screener.py`, `test_async_screener.py`).
- [ ] Task: Deprecate/Remove redundant standalone screener files.
- [ ] Task: Final Report.
