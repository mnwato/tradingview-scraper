# Spec: Crypto Discovery-Selection Factor Alignment

## 1. Goal
Mathematically align the **Discovery** stage (Screener Scans) with the **Natural Selection** stage (Log-MPS 3.2 Selection Engine). This prevents "Factor Drift" where candidates are selected in Discovery using criteria that are later rejected or contradicted by the Selection Engine.

## 2. Institutional Standards
To pass this audit, all Crypto configs must adhere to:
- **Liquidity Floor**: `Value.Traded >= 10,000,000` ($10M USD). This matches the institutional baseline used in `scoring.py` for Crypto assets.
- **Momentum Horizons**: Synchronize with `test_window` (21d) and `train_window` (126d).
    - Use `Perf.1M` (Monthly) as the primary trend filter.
    - Use `Perf.3M` (Quarterly) as the secular trend filter.
- **Volatility Ceiling**: `Volatility.D <= 35.0` or `ATR/close <= 0.3`. This prevents extreme "flash" assets from entering the clustering pipeline where they distort the correlation matrix.
- **Inheritance**: All strategy configs MUST inherit from a `base_preset` (e.g., `presets/base_binance_spot.yaml`) to ensure global parameter updates propagate instantly.

## 3. Factor Synchronization
| Factor | Discovery Metric | Selection Engine Logic | Alignment Status |
| :--- | :--- | :--- | :--- |
| **Liquidity** | `Value.Traded` ($10M) | `calculate_liquidity_score` ($10M baseline) | **Aligned** |
| **Trend** | `Perf.1M`, `Perf.3M` | Window-local Mean Returns | **Synchronized** |
| **Volatility** | `Volatility.D` (35%) | Standard Deviation (Clipped) | **Aligned** |
| **Breadth** | `ADX` >= 10 | MPS Multiplicative Scoring | **Aligned** |
