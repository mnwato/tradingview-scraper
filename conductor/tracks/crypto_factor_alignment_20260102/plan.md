# Plan: Crypto Discovery-Selection Factor Alignment

## Phase 1: Institutional Presets
- [x] **Task**: Create `configs/presets/base_crypto_spot.yaml` with $10M floor.
- [x] **Task**: Create `configs/presets/base_crypto_perp.yaml` (inherits from spot).
- [x] **Task**: Update exchange-specific presets (`base_binance_spot.yaml`, `base_okx_perp.yaml`, etc.) to inherit from core crypto presets.

## Phase 2: Strategy Config Refactoring
- [x] **Task**: Refactor 16 Trend Scanners (`crypto_cex_trend_*.yaml`) to use `base_preset` inheritance.
- [x] **Task**: Align `momentum` horizons in all trend scanners to institutional standard (1M/3M).
- [x] **Task**: Remove redundant `exchanges`, `markets`, and `volume` filters from strategy configs.

## Phase 3: Base Universe Alignment
- [x] **Task**: Refactor 8 Base Scanners (`crypto_cex_base_top50_*.yaml`) to use `base_preset`.
- [x] **Task**: Refactor multi-exchange base configs (`crypto_cex_base_top50.yaml`, `..._perp.yaml`, `..._dated.yaml`).

## Phase 4: Validation
- [x] **Task**: Perform dry-runs of Binance Spot/Perp to verify payload correctness.
- [x] **Task**: Verify that `trend` filters are disabled in base universe scans but active in strategy scans.
- [x] **Task**: Standardize `columns` across all Base Presets (Crypto, Stocks, ETF, Forex, Futures) to include secular trend horizons (6M, Y, YTD).
- [x] **Task**: Execute Live Scanners and verify `Value.Traded` and `Perf.*` consistency in exported JSON.
