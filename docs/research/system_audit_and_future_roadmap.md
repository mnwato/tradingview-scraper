# Quantitative Pipeline Audit & Strategic Roadmap

This document consolidates findings from the 2025-12-26 system audit and outlines the strategic plan for Phase 5 development to enhance the operability and robustness of the portfolio generation lifecycle.

## 1. Executive Summary
The current system has successfully implemented a multi-asset, cluster-aware quantitative pipeline. It excels at handling asset redundancy and identifying secular regimes. However, the system relies on static thresholds and lacks automated rebalancing tracking ("State Management"), which limits its effectiveness in fast-moving market regimes.

## 2. Audit Findings: Identified Weaknesses

### Stage 1: Discovery & Selection
- [x] **Fixed Diversity Caps**: The system now supports configurable `UNIVERSE_TOP_N` and Alpha Ranking.
- [x] **Metadata Timing**: Metadata enrichment is now integrated into the selection and prep cycle.
- [ ] **Raw Pool Bloat**: Currently backfilling 100% of raw candidates (~140 symbols) for 200 days before any pruning, causing significant data waste and rate-limit friction.

### Stage 2: Data Resilience
- [ ] **Rigid Lookback**: All assets are forced to a 200-day window. Recently listed high-momentum assets may be dropped.
- [x] **Throttling Inefficiency**: Batching is active, and `Selective Sync` is implemented.
- [x] **Self-Healing**: Automated repair pass is integrated into `make data-repair`.

### Stage 3: Hierarchical Analysis
- [x] **Static Cutting Threshold**: Regime-adaptive clustering is now implemented.
- [x] **Labeling Noise**: Mode-selection and institutional sector overrides are active.

### Stage 4: Risk Optimization
- [x] **Binary Fragility**: Fragility scores (CVaR) are now calculated and audited.
- [x] **Fragility-Adjusted Objective**: Weights are penalized by fragility in `ClusteredOptimizerV2`.
- [x] **Uniform Intra-Cluster Weighting**: Hybrid Layer 2 (Momentum-Volatility blend) is implemented.

### Stage 5: Reporting & Implementation
- [x] **Categorization Gaps**: Explicit institutional mapping for Fixed Income and Metals is active.
- [x] **Visual "Dust"**: Minimum implementation floor (0.1%) is enforced in reports.
- [x] **Integrated Risk Tree**: Nested sub-clustering and high-res clustermaps are integrated.
- [x] **Implementation Dashboard**: Terminal-based `rich` dashboard (`make display`) is fully operational.

## 3. Phase 5 Roadmap: Dynamic Constraints & State Management

### A. Tiered Intelligence Discovery (Priority: High)
- **Discovery-Alpha Gate**: Implement a Stage 1 filter in `select_top_universe.py` to limit the raw pool to the Top 25 assets per category based on Discovery Alpha (`Liquidity + Trend + Vol`).
- **Two-Pass Statistical Pruning**:
    - **Pass 1 (Lightweight)**: Fetch only **60 days** of history for the truncated raw pool.
    - **Pass 2 (Natural Selection)**: Execute hierarchical clustering on the 60-day window to identify winners.
    - **Pass 3 (High Integrity)**: Fetch full **200-day** history *only* for the Natural Selection winners.
- **Strategic Rationale**: Reduces deep backfill volume by 50-60% while maintaining exchange fidelity (allowing venues to compete statistically).

### B. Dynamic Risk Constraints (Priority: High)
- **CVaR-Penalized Optimization**: [x] Implemented.
- **Regime-Adaptive Clustering**: [x] Implemented.
- **Fragility Constraints**: Automatically penalize clusters with high CVaR directly in the objective function.

### C. Alpha-Weighted Internal Allocation (Priority: High)
- **Hybrid Layer 2**: [x] Implemented Momentum-Volatility blend.

### D. State-Aware Workflows & State Tracking (Priority: Medium)
- **Portfolio State Engine**: [x] Implemented `scripts/track_portfolio_state.py`.
- **Selective Sync**: [x] Implemented.

## 4. Operational Improvement Progress
- [x] **Gist Automation**: `make gist` now syncs all 5 risk reports + images.
- [x] **Natural Selection**: Initial cluster-based filtering is active.
- [x] **CLI Heatmap**: Unicode-based correlation heatmap (`make heatmap`) is operational.

## 5. Operational Improvement Suggestions
1. **Recovery Loops**: Implement a `make data-repair` target for high-intensity sequential retries.
2. **Institutional Guardrails**: Integrate `make audit` into CI/CD.
3. **Threshold Sensitivity Analysis**: Visualize cluster count vs. distance threshold.

## 6. Next Steps
1. Refactor `select_top_universe.py` with Alpha-Gate truncation.
2. Implement Tiered Backfill (60d/200d) in `Makefile`.
3. Integrate real-time liquidity into Lead Asset selection.
