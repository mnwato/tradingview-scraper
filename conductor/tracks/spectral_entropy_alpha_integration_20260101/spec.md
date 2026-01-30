# Specification: Spectral & Entropy Alpha Integration

## 1. Overview
This track integrates advanced mathematical filters (Permutation Entropy, Hurst Exponent, Efficiency Ratio) directly into the **Natural Selection (Pruning)** stage of the quantitative pipeline. By applying these metrics at the asset level during selection, we can veto "Maximum Uncertainty" symbols and prioritize "High-Efficiency" trends that are mathematically distinguishable from random noise.

## 2. Functional Requirements

### 2.1 Predictability Utility Implementation
- Create a shared utility `tradingview_scraper/utils/predictability.py` to compute:
    - **Kaufman's Efficiency Ratio (ER)**: `(Absolute Price Change over N days) / (Sum of Absolute Daily Changes over N days)`.
    - **Permutation Entropy (PE)**: Measure of structural randomness.
    - **Hurst Exponent (H)**: Measure of long-term memory (Trending vs Mean-Reverting vs Random Walk).
- Refactor `MarketRegimeDetector` to utilize this shared utility for its global calculations.

### 2.2 Natural Selection Integration (V3 Engine)
- Update `SelectionEngineV3` and `SelectionEngineV3_1` in `tradingview_scraper/selection_engines/engines.py` to include:
    - **Entropy Veto**: Discard symbols with PE > 0.9 (Pure Noise).
    - **Efficiency Veto**: Discard symbols with ER < 0.1 (Excessive Chop).
    - **Hurst-Random-Walk Veto**: Discard symbols where 0.45 < Hurst < 0.55 (Random Walk zone).
- **Scoring Factor**: Integrate ER as a multiplicative factor in the MPS score to favor "clean" price action.

### 2.3 Audit & Reporting
- Decisions made by these new filters MUST be recorded in the `vetoes` dictionary returned by the selection engine.
- The `audit.jsonl` ledger must capture these specific veto reasons (e.g., "Vetoed: High Entropy (0.94)").

## 3. Non-Functional Requirements
- **Performance**: Predictability calculations must be vectorized where possible to handle ~200 symbols efficiently.
- **Backward Compatibility**: Ensure `SelectionEngineV2` remains unaffected.

## 4. Acceptance Criteria
- `SelectionEngineV3` successfully disqualifies assets based on entropy and efficiency thresholds.
- `scripts/comprehensive_audit.py` or `scripts/generate_selection_report.py` shows the count of predictability-based vetoes.
- A backtest demonstrates that the "Spectral Filtered" universe has a higher "Selection Alpha" (Return of Selected vs Return of Discovery Pool) compared to the baseline.

## 5. Out of Scope
- Implementing these filters in the initial Discovery (Screener) phase due to high-fidelity data requirements.
- Adaptive thresholding (thresholds remain static per configuration).
