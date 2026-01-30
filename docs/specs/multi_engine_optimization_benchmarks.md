# Multi-Engine Optimization Benchmarks (Implemented)

This specification defines the integration of advanced portfolio optimization libraries into the production pipeline. As of Jan 2026, the framework is fully profile-centric and validated across the 4D Tournament Matrix.

## 1. Integrated Engines

The following engines are implemented using a unified `BaseRiskEngine` interface. Universal fallbacks have been removed to ensure library-specific variance:

| Engine | Library | Profile Native Focus |
| :--- | :--- | :--- |
| **Custom (Internal)** | `cvxpy` | Research baseline, standard quadratic objectives |
| **skfolio** | `skfolio.optimization` | Native HRP, Risk Budgeting, Equal-Weighted |
| **Riskfolio-Lib** | `riskfolio.Portfolio` | native Risk Parity, HRP (codependence), CVaR |
| **PyPortfolioOpt** | `pypfopt.efficient_frontier` | Standard HRP, Efficient Frontier |
| **CVXPortfolio** | `cvxportfolio.Policy` | Multi-Period Optimization (MPO), MVO |

## 2. Standardized Portfolio Profiles

The framework benchmarks institutional risk management paradigms. Profile definitions are standardized in `docs/specs/optimization_engine_v2.md`. All engines must implement these profiles natively:

- **`market`**: Institutional baseline (benchmark symbols, equal-weight).
- **`benchmark`**: Research baseline (active universe, asset-level equal-weight).
- **`equal_weight`**: Hierarchical equal weight (cluster-level EW, HERC intra).
- **`hrp`**: Hierarchical Risk Parity (Library-specific tree bisection).
- **`risk_parity`**: Equal Risk Contribution (Library-specific native solvers).
- **`max_sharpe`**: Optimized return-to-risk ratio.
- **`barbell`**: Sleeve-based sleeve strategy.
- **`min_variance`**: Absolute risk minimization.
- **`adaptive`**: Regime-driven profile switcher (meta profile).

Note: `raw_pool_ew` is a backtest-only, selection-alpha diagnostic baseline and should not be used as a benchmark baseline unless stability/invariance criteria are met (see `docs/specs/optimization_engine_v2.md`).

## 3. Benchmarking Framework

### 4D Matrix Validation (Tournament Mode)
The `BacktestEngine` executes a 4D cross-product:
1.  **D1: Selection Mode** (v2, v3)
2.  **D2: Engines** (All 5 backends)
3.  **D3: Profiles** (Standardized suite)
4.  **D4: Simulators** (cvxportfolio, nautilus, vectorbt, custom)

### Simulator Parity Breakthrough (Jan 2026)
Institutional baselines achieved **absolute parity (20.67%)** across all backends:
- **`cvxportfolio`**: High-fidelity execution with N+1 alignment.
- **`nautilus` / `custom`**: Standardized with turnover-aware friction.

### Engine Caveats
- **Riskfolio-Lib**: Audit Run `20260107` revealed a **negative correlation (-0.92 to -0.95)** between Riskfolio's HRP implementation and standard SciPy/Skfolio implementations.
    - **Status**: **Experimental Use Only**.
    - **Note**: The alignment fix (`linkage="ward"`) applied in Phase 13 did *not* resolve the structural divergence. Users should prefer `skfolio` or `custom` engines for production HRP.

## 4. Performance-Churn Frontier (Jan 2026)

Comparative audits have established a clear trade-off between risk control and execution efficiency:

| Profile | Realized Sharpe (Avg) | Realized MDD (Avg) | Avg. Turnover | Status |
| :--- | :--- | :--- | :--- | :--- |
| **`adaptive`** | **2.65** | **-4.9%** | Moderate | **Champion** |
| **`barbell`** | 2.65 | -4.9% | Low (20%) | **Production Default** |
| **`risk_parity`** | 1.64 | -4.4% | Moderate | Turbulent Defense |
| **`market`** | 0.74 | -5.1% | Ultra-Low | Benchmark |

### Key Secular Insights:
- **Profile Independence**: The removal of the "Universal Fallback" trap revealed significant variance in native HRP solvers (e.g., `skfolio` vs `cvxportfolio`).
- **Resilience in CRISIS Regimes**: **Risk Parity** emerged as the 2025 winner, providing superior stability through turbulent regimes.
- **Structural Risk Control**: Validated that HRP's risk reduction is structural (derived from the correlation tree) and remains stable even when individual asset correlations drift.
- **Numerical Stability**: Standardized on **Tikhonov Regularization** ($10^{-6} \cdot I$) to resolve CVXPY "Variable must be real" solver failures.
