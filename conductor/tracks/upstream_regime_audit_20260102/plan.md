# Track: Upstream Regime Detection Audit & Refinement (2026-01-02)

## Objective
Audit and refactor the `MarketRegimeDetector` to align with Jan 2026 institutional standards, ensuring robust, macro-aware state classification for the quantitative pipeline.

## Status snapshot
- **Logic**: Multi-factor weighted score + 2-state HMM + Quadrant Analysis.
- **Improvements**: Standardized weights (sum=1.0), thresholds (0.7/1.8), and implemented audit trail.
- **Issues**: Identified split-weight inconsistencies (3% vs 8%) and Adaptive Engine mapping gaps.

## Tasks

### Phase 1: Mathematical & Logic Audit
1. [x] **Normalization Audit**: Verified component metrics are properly scaled.
2. [x] **Threshold & Weight Standardization**: Re-aligned `regime.py` with `regime_detection_standards.md`.
3. [x] **Unified Classification**: Integrated quadrant detection and HMM confirmation.
4. [ ] **Mathematical Integrity**: Verify `Hurst` and `DWT` energy ratios against benchmark packages (nolds/arch).
5. [ ] **Cross-Sectional Audit**: Evaluate "Global Proxy" for survivorship bias and outlier skewing.

### Phase 2: Refinement (Regime Detection 2.0)
1. [ ] **Dynamic Weighting**: Implement SNR-based dynamic weighting for composite score.
2. [ ] **3-State HMM**: Upgrade to a 3-state HMM (Quiet, Trending, Volatile).
3. [ ] **Regime History Visualization**: Create `scripts/visualize_regime_history.py`.
4. [x] **Downstream Consistency Audit**: Completed. Identified discrepancies in `TURBULENT` weights and `Adaptive` mapping.

### Phase 3: Downstream Integration & Feedback
1. [x] **Optimizer Consistency Review**: Completed. Identified gaps in `AdaptiveMetaEngine` and split-weight inconsistencies.
2. [x] **Downstream Refinement (Action)**:
    - [x] Aligned `REGIME_SPLITS` to 15% (QUIET), 10% (NORMAL), 5% (TURBULENT), 3% (CRISIS).
    - [x] Updated `AdaptiveMetaEngine` to support `TURBULENT` -> `hrp` and `NORMAL` -> `max_sharpe`.
3. [ ] **Bayesian Feedback Loop**: Implement auto-selection of objective functions based on `regime_audit.jsonl`.

## Verification
- Run `scripts/research_regime_v2.py`: Passed (QUIET score ~0.55).
- Validate audit trail entries: Passed (JSONL generated with full metrics).
- Ensure unit tests pass: Passed.
