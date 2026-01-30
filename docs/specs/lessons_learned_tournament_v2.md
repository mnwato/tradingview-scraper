# 🎓 Lessons Learned: Tournament V2 & 4D Multi-Engine Benchmarking

## Overview
The Tournament V2 and subsequent 4D Matrix runs (Jan 2026) provided critical insights into CARS 2.0 (v2) selection, multi-simulator parity, and the challenges of benchmarking during CRISIS regimes.

## 1. Selection Intelligence (V2 Spec)
- **Metadata dependency**: Selection Specs V2 and V3 are highly dependent on execution metadata (`tick_size`, `lot_size`, `price_precision`). Institutional assets (AAPL, QQQ) are vetoed if this metadata is missing, leading to a degraded pool. The restoration of institutional defaults was critical for diversified performance.
- **Hierarchical Resilience**: The system successfully clusters assets even when simulators fail. Pruning logic effectively groups assets by return correlation and volatility units.
- **V2 vs V3 Delta**: V2 (CARS 2.0) outperformed V3 by up to **1.5 Sharpe points** in trending 2025 markets. V3's Darwinian health gates proved overly conservative, though superior for tail-risk protection in stagnant regimes.

## 2. Optimization Engine Dynamics
- **Solver Parity & Divergence**: 
    - Initial runs showed identical results due to a **"Universal Fallback"** trap where all engines defaulted to the same CVXPY code.
    - Post-refactor, engines now use **native library solvers** (e.g., `skfolio.HierarchicalRiskParity`, `riskfolio.rp_optimization`), enabling true benchmarking of library-specific alpha.
- **skfolio Resilience**: Validated as the most stable engine during CRISIS regimes. Native HRP implementations outperformed frictionless baselines by managing turnover more effectively.

## 3. Simulator Parity & Fidelity
- **Market Baseline Parity**: Achieved absolute return parity (**20.67%**) across `cvxportfolio`, `nautilus`, and `custom` simulators for the institutional benchmark.
- **The alignment breakthrough**:
    - Resolved the "off-by-one" day leak in `cvxportfolio` by implementing a **1-day look-ahead slice**.
    - Standardized **Turnover-Aware Friction** in research baselines, eliminating artificial " frictionless optimism."
- **Turnover Standard**: Unified on `sum(abs(trades)) / 2` across all backends.

## 4. Technical Debt & Fixes
- **Profile-Centric Architecture**: Transitioned from engine-driven logic to profile-driven optimization. Redundant engines (like the `market` engine) were replaced by standardized EW profiles.
- **Atomic Audit Integrity**: Implemented Unix **file locking (`fcntl`)** for shared audit files to prevent JSON corruption during high-concurrency runs.
- **Numerical Stability**: Standardized on **Tikhonov Regularization** ($10^{-6}$) for all covariance-based optimizers.
