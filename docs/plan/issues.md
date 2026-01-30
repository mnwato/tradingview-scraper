# Project Implementation Roadmap: 2025 Standard

This document tracks the phased development of the TradingView Scraper institutional quantitative platform.

### Phase 1 through 18 (Finalized)
- Core Infrastructure, Metadata, Discovery, 3D Tournament, Unified Metrics, and VectorBT Integration.

### Phase 19 — Dynamic Universe Rebalancing & Adaptive Allocation (Finalized)
1. **Dynamic Pruning**: Refactor `BacktestEngine` to re-execute Natural Selection at each rebalancing window.
2. **Momentum Alpha Gate**: Implement a hard momentum filter in `natural_selection.py` to exclude losing clusters.
3. **Concentrated Alpha**: Update production manifest with tighter thresholds (`THRESHOLD=0.55`) and single-asset clusters (`TOP_N=1`).
4. **Daily Rebalancing Parity**: Align `ReturnsSimulator` to model daily target rebalancing for fair benchmarking.
5. **Turnover Regularization**: Integrate L1-norm turnover penalties into the custom `cvxpy` optimizer.

### Phase 20 — Industrial Alpha Hardening & Implementation Audit
1. **Selection Alpha Review**: Programmatically compare "Discarded" vs "Selected" assets to validate the Natural Selection gate.
2. **Cluster Homogeneity**: Enforce a minimum correlation within clusters to prevent grouping fundamentally divergent assets.
3. **Institutional Resume**: Finalize the Strategy Resume with 200-day realized secular metrics beat-rate against SPY.

### Phase 21 — 2026 Flow-Dev Audit Remediation (Planned)
1. **Lookback Wiring**: Ensure `LOOKBACK` propagates to `PORTFOLIO_LOOKBACK_DAYS` so dev profiles honor 60d windows.
2. **Tournament Defaults**: Fix `backtest_engine.py` empty-arg parsing so simulators/engines/profiles default correctly.
3. **Barbell Availability**: Generate antifragility stats before optimization or explicitly skip barbell with a warning.
4. **Calendar Alignment**: Remove zero-padding for TradFi and align returns on market-day calendars.
5. **Canonical Latest**: Standardize the authoritative "latest" run pointer to avoid stale audits.
