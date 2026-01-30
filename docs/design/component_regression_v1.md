# Design: Component-by-Component Regression (v1)

## 1. Objective
To systematically isolate and repair the technical indicators that are contributing most to the divergence between the replicated `Recommend` signal and the TradingView ground truth.

## 2. Analysis Strategy

### 2.1 The "Worst Offender" Identification
We will parse the `feature_parity_results.json` generated in Phase 700 to calculate the Mean Absolute Error (MAE) for each of the 28 sub-indicators (e.g., `RSI`, `Stoch.K`, `ADX`).

**Priority Triage**:
1.  **Critical (> 20% deviation)**: Must fix. Likely a fundamental logic error (e.g., smoothing type).
2.  **High (> 10% deviation)**: Should fix. Likely a parameter mismatch (e.g., lookback period).
3.  **Low (< 5% deviation)**: Acceptable noise (floating point differences).

### 2.2 Isolation Tests
We will create a new test suite `tests/test_component_isolation.py` that mocks input OHLCV data and asserts the output of specific `TechnicalRatings` methods against known reference values derived from manual TV Screener checks.

## 3. Tuning Targets (Hypothesis)

| Component | Hypothesis | Experiment |
| :--- | :--- | :--- |
| **RSI** | TV uses Wilder's Smoothing (RMA), we use SMA/EMA? | Verify `pandas-ta` default is RMA. |
| **MACD** | Signal line smoothing method mismatch. | Try EMA vs SMA for signal line. |
| **CCI** | Constant factor (0.015) difference. | Check scaling constant. |
| **ADX** | DX smoothing method. | RMA vs EMA for DX. |

## 4. Implementation Plan
1.  Analyze existing audit JSON.
2.  Write isolation tests for the worst offender.
3.  Tune `TechnicalRatings` logic.
4.  Re-run audit.
5.  Repeat until all critical deviations are resolved.
