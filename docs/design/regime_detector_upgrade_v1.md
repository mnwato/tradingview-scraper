# Design Specification: Regime Detector Upgrade (v1.0)

## 1. Objective
Review, audit, and upgrade the `MarketRegimeDetector` to align with the "Spectral Intelligence" strategic principle and ensure robust, point-in-time correct regime identification for adaptive portfolio management.

## 2. Current State Analysis
- **Class**: `MarketRegimeDetector` in `tradingview_scraper/regime.py`.
- **Inputs**: `pd.DataFrame` of asset returns.
- **Logic**: Composite score of:
    - Volatility Ratio (35%)
    - DWT Turbulence (25%)
    - Volatility Clustering (15%)
    - Permutation Entropy (10%)
    - Hurst Exponent (10%)
    - Stationarity (5%)
    - Tail Risk (Kurtosis) (+15% adder)
- **Output**: `CRISIS`, `QUIET`, `NORMAL`, `TURBULENT`, `INFLATIONARY_TREND`, `STAGNATION`.

## 3. Audit Findings & Requirements
1.  **Spectral Intelligence**: The current implementation *does* use DWT Turbulence (`calculate_dwt_turbulence`) and Entropy (`calculate_permutation_entropy`). This requirement is met foundationally.
2.  **Point-in-Time**: The detector operates on a `returns` DataFrame. If this DataFrame represents the "known history up to time T", then it is point-in-time correct. The caller (`research_regime_v3.py` or `BacktestEngine`) is responsible for slicing the data correctly.
3.  **Robustness**:
    - `_dwt_turbulence` falls back to 0.5.
    - `_hurst_exponent` falls back to 0.5.
    - **Issue**: `detect_quadrant_regime` has hardcoded thresholds (`ann_return > 0.05`). This might be brittle across different asset classes (Crypto vs Bonds).
    - **Issue**: `_hmm_classify` uses `GaussianHMM` which can be unstable or slow. It captures "Hidden States" but might not be robust for all data lengths.

## 4. Upgrade Plan

### 4.1 Refactoring `tradingview_scraper/regime.py`
- **Typing**: Improve type hints.
- **Robustness**: Add checks for `NaN` and infinite values in input returns *before* calculation to prevent silent failures or bad metrics.
- **Configuration**: Expose thresholds (like `ann_return > 0.05`) as configurable parameters or derive them dynamically (e.g., relative to a benchmark or historical mean).
- **Testing**: Add a proper test suite. Currently, reliance is on integration tests.

### 4.2 Test Plan (`tests/test_regime_detector.py`)
- **Fixture**: Synthetic returns for different regimes:
    - **Bull Market**: Low vol, positive trend.
    - **Bear Market / Crisis**: High vol, negative trend, spikes.
    - **Sideways**: Low vol, zero trend.
- **Tests**:
    - `test_detect_crisis`: Verify "CRISIS" label for high-vol negative returns.
    - `test_detect_quiet`: Verify "QUIET" or "NORMAL" for low-vol positive returns.
    - `test_score_components`: Verify individual metrics (Hurst, Entropy) behave as expected on synthetic signals (e.g., Sine wave vs Random Noise).
    - `test_robustness`: Pass empty DF, too short DF, DF with NaNs.

## 5. Integration
No major API changes expected. The `BacktestEngine` and `research_regime_v3.py` utilize the high-level `detect_regime` method.

## 6. Success Criteria
- All tests pass.
- `research_regime_v3.py` runs without error on the current lakehouse data.
