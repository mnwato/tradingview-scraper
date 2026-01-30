# Implementation Plan: Hierarchical Risk Parity (HRP)
**Track ID**: `hierarchical_risk_parity_20251221`
**Status**: Planned

## 1. Objective
Improve portfolio resilience by implementing Hierarchical Risk Parity (HRP). This approach uses graph theory and clustering to group correlated instruments, ensuring that risk is diversified across unique market drivers rather than just individual symbols.

## 2. Phases

### Phase 1: Correlation Audit & Clustering
Goal: Map the "Hidden Structure" of the multi-asset universe.
- [ ] Task: Research and prototype Hierarchical Clustering (HCL) using scipy/sklearn.
- [ ] Task: Implement "Quasi-Diagonalization" to reveal the true block-structure of the covariance matrix.
- [ ] Task: Visualize the Asset Dendrogram to verify cluster logic.

### Phase 2: HRP Solver Implementation
Goal: Build the weight allocation engine.
- [ ] Task: Implement the Recursive Bisection algorithm.
- [ ] Task: Build the `HierarchicalRiskParity` class in `tradingview_scraper/risk.py`.
- [ ] Task: Integrate "Clustered Volatility" penalties.

### Phase 3: Validation & Benchmarking
Goal: Prove the superiority of HRP in high-correlation regimes.
- [ ] Task: Compare HRP vs. Standard Risk Parity on "Effective Number of Assets" (Entropy).
- [ ] Task: Backtest stability during a crypto-market regime shift.
- [ ] Task: Final Report.
