# Plan: Calendar-Aware Data Health Audit

## Phase 1: Metadata & Utils
- [x] **Task**: Update `MetadataCatalog.get_instrument` to consistently return `DataProfile`.
- [x] **Task**: Enhance `get_us_holidays()` to cover full 2025/2026 major windows.

## Phase 2: Refactor audit_antifragility.py
- [x] **Task**: Implement `calculate_effective_gaps(symbol, returns, profile)` helper.
- [x] **Task**: Filter weekend/holiday dates from the returns matrix when checking gaps for non-crypto assets.
- [x] **Task**: Update "Gate 1 (Health)" warning logic to reduce noise.

## Phase 3: Update validate_portfolio_artifacts.py
- [x] **Task**: Synchronize gap detection logic with `LakehouseStorage.detect_gaps`.
- [x] **Task**: Refine `FRESHNESS_THRESHOLD_DAYS_TRADFI` to handle long holiday weekends.

## Phase 4: Verification
- [x] **Task**: Rerun `make audit-health` and verify non-crypto assets are no longer 30%+ "Gaps" during holiday weeks.

## Phase 5: exchange_calendars Integration
- [x] **Task**: Add `exchange_calendars` to project dependencies.
- [x] **Task**: Map TradingView exchange codes to `exchange_calendars` names in `metadata.py`.
- [x] **Task**: Implement `get_exchange_calendar(symbol, profile)` utility.
- [x] **Task**: Refactor `LakehouseStorage.detect_gaps` to use library-backed trading schedules.
- [x] **Task**: Refactor `audit_antifragility.py` to use library-backed trading schedules.
