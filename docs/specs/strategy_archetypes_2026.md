# Specification: Quantitative Strategy Archetypes (Jan 2026)

This document defines the formal technical standards for the core strategies and detection systems in the TradingView Scraper framework.

## 1. Antifragile Barbell Profile

The Barbell profile implements structural isolation between high-optionality alpha and a stable risk-balanced core.

| Component | standard | Rationale |
| :--- | :--- | :--- |
| **Aggressors (default: 10%)** | Top `max_aggressor_clusters` clusters by `Antifragility_Score` (**n** leaders per cluster; currently **n=1**) | Convexity sleeve with factor diversification. |
| **Core (default: 90%)** | Core HRP sleeve over the remaining clusters | Capital preservation + diversified stability. |
| **Core Engine** | `hrp` (engine-native; see `docs/specs/hrp_implementation_parity.md`) | Defensive allocator used as the barbell core sleeve. |
| **Adaptive Scaling** | Default aggressor schedule: **QUIET 15% / NORMAL 10% / TURBULENT 8% / CRISIS 5%** (override by explicitly setting `aggressor_weight`) | Preserve core under stress while retaining optionality. |

## 2. Native Hierarchical Risk Parity (HRP)

The `hrp` profile provides the "capital preservation" standard using engine-native hierarchical risk parity implementations.

- **Canonical reference**: See `docs/specs/hrp_implementation_parity.md` for exact distance/linkage per backend.
- **skfolio implementation**: Ward linkage + Distance Correlation + RiskMeasure=Standard Deviation (per `tradingview_scraper/portfolio_engines/engines.py`).
- **Role**: Defensive baseline and the core optimization logic for the Barbell sleeve.

## 3. All Weather Quadrant Detector

The `MarketRegimeDetector` classifies market environments into four quadrants to drive adaptive strategy selection.

| Axis | System Proxy | Statistical Standard |
| :--- | :--- | :--- |
| **Growth Axis** | Annualized Return | Identifies Expansion vs. Contraction. |
| **Stress Axis** | Vol Ratio + DWT Noise | Identifies Stability vs. Turbulence. |

### The Quadrant Matrix:
1. **`EXPANSION`**: High Growth / Low Stress $\rightarrow$ **Adaptive Target**: `max_sharpe`.
2. **`INFLATIONARY_TREND`**: High Growth / High Stress $\rightarrow$ **Adaptive Target**: `barbell`.
3. **`STAGNATION`**: Low Growth / Low Stress $\rightarrow$ **Adaptive Target**: `min_variance`.
4. **`CRISIS`**: Low Growth / High Stress $\rightarrow$ **Adaptive Target**: `hrp`.

## 4. Institutional Fidelity Standards
- **Ledoit-Wolf Shrinkage**: Universal for all covariance-dependent steps.
- **L2 Regularization (default $\gamma=0.05$, configurable)**: Guard against overfitting in all non-HRP optimizations.
- **Audit Requirement**: All transitions and weights must be recorded in the SHA-256 chained ledger.
