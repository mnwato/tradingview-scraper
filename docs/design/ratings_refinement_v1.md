# Design: Ratings Refinement (v1)

## 1. Objective
To refine the `Recommend.Other` (Oscillator) component of the technical ratings to improve directional (Sign) accuracy, which currently lags behind rank correlation.

## 2. Tuning Targets

### 2.1 RSI Smoothing
- **Current**: Standard RSI (Wilder's Smoothing).
- **Hypothesis**: TradingView might use a different smoothing period or method for the rating logic vs the visual indicator.
- **Experiment**: Test 14-period SMA vs RMA for RSI calculation.

### 2.2 Stochastic RSI Alignment
- **Current**: `ta.stochrsi` defaults.
- **TV Logic**: StochRSI K/D lines are often smoothed with SMA(3).
- **Action**: Explicitly define smoothing parameters `smooth_k=3`, `smooth_d=3`.

### 2.3 Ultimate Oscillator
- **Current**: Standard 7, 14, 28.
- **TV Logic**: Check if weights are standard (4, 2, 1).

## 3. Implementation Plan
1.  **Refactor**: Update `calculate_recommend_other_series` in `technicals.py` with tuned parameters.
2.  **Verify**: Run `audit_feature_parity.py` and check if `Sign Accuracy` improves from 33%.
3.  **Regression**: Run `test_vectorization_parity.py` to ensure scalar/vector equivalence is maintained.
