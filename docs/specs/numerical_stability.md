# Numerical Stability & Reporting Standards

## 1. Numerical Stability

### Stable Sum Gate
- **Problem**: Mixed-direction or Short-only portfolios can have near-zero net weights, causing division-by-zero errors in rebalancing calculations.
- **Solution**: The **Stable Sum Gate** enforces a check on the sum of absolute weights.
- **Threshold**: $W_{sum} < 1e-6$ triggers a fallback or normalization adjustment.

### Selection Scarcity Protocol (SSP)
- **Problem**: Optimization engines (especially convex solvers) yield unstable results when the number of assets ($N$) is small.
- **Requirement**: Selection pipelines MUST enforce a **15-winner floor**.
- **Mechanism**: If $N < 15$ after primary filtering, the system relaxes thresholds (HTR loop) to recruit more candidates.

### Dynamic Ridge Scaling
- **Problem**: Covariance matrices can be ill-conditioned.
- **Solution**: Iterative shrinkage (Ridge Regularization).
- **Bound**: Kappa (Condition Number) must be $< 5000$.

## 2. Reporting Purity

### Identity-Aware Reporting
- **Principle**: Reporting scripts must never assume fixed indices or structures.
- **Implementation**: Utilize `.get()` for all metadata lookups to handle missing fields gracefully.

### Hierarchical Data Structure
- **Requirement**: Restructure flat tournament data into nested hierarchies (e.g., `Strategy -> Profile -> Metric`).
- **Goal**: Stable Markdown generation and reliable "tearsheet" production.

### Audit Ledger
- **File**: `audit.jsonl`
- **Requirement**: Every critical decision (selection, weight override, fallback trigger) must be logged.
- **Integrity**: Never bypass the audit chain for manual interventions.
