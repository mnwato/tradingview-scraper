# Plan: End-to-End Pipeline Factor Audit

## Phase 1: Configuration & Logic Review
- [x] **Task**: Audit `configs/*.yaml` for scanner factor thresholds (Momentum, ADX, Volatility).
- [x] **Task**: Review `SelectionEngineV3_2` factor extraction logic in `tradingview_scraper/selection_engines/engines.py`.
- [x] **Task**: Identify specific symbols that pass `Discovery` but are vetoed by `Log-MPS` due to ECI or Predictability. (Documented in `AUDIT_REPORT.md`)

## Phase 2: Factor Alignment & Config Layering
- [x] **Task**: Align scanner momentum horizons with selector window lookbacks (added `Perf.1M` to ETF config).
- [x] **Task**: Standardize `Value.Traded` usage for liquidity across the pipeline (Implemented market-aware baseline in `scoring.py`).
- [x] **Task**: **Layered Config Refactoring**: 
    - [x] Create/Update `configs/presets/base_*.yaml` for core markets.
    - [x] Move all Liquidity/Volatility guards to Base Presets.
    - [x] Refactor strategy configs (`configs/*.yaml`) to inherit from Base Presets.
- [x] **Task**: **Systematic Alignment**: Propagate `Perf.1M` and `Perf.W` momentum filters to remaining strategy-layer configs.
- [x] **Task**: **Volatility Guard Review**: Audit the static `35%` volatility cap in the Base Presets.
- [x] **Task**: **Pre-Selection Estimator**: Implement a lightweight ECI check in `scripts/enrich_candidates_metadata.py`.
- [x] **Task**: Refine ECI hurdle logic to handle varying market regimes (TURBULENT vs QUIET).

## Phase 3: Final Validation & Instrumentation
- [x] **Task**: Update `BacktestEngine` to log "Factor Mismatch" events.
- [x] **Task**: Rerun `scripts/unified_benchmark_2026.py` with aligned configs.
- [x] **Task**: Update `docs/specs/selection_intelligence_v1.md` with the unified factor model and new liquidity baselines.
