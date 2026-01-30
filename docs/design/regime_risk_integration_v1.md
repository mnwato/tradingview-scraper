# Design Specification: Regime-Risk Integration (v1.0)

## 1. Objective
Integrate the `MarketRegimeDetector` into the `BacktestEngine` to dynamically adjust portfolio risk parameters based on the detected market state. This replaces the hardcoded "NORMAL" regime.

## 2. Current Gap
- `MarketRegimeDetector` is robust and validated (Phase 250/260).
- `CustomClusteredEngine` has logic to adapt L2 regularization and Barbell aggressor weights based on regime.
- **BUT**: `BacktestEngine` currently hardcodes `regime_name = "NORMAL"`.

## 3. Integration Plan

### 3.1 Backtest Engine Update
- Instantiate `MarketRegimeDetector` in `BacktestEngine.__init__`.
- In `run_tournament` loop (per window):
    - Slice returns for the current window (lookback 64 days min).
    - Call `detector.detect_regime(window_returns)`.
    - Map the output `(regime, score, quadrant)` to `regime_name` passed to `EngineRequest`.

### 3.2 Mapping Logic
The detector returns `CRISIS`, `QUIET`, `NORMAL`, `TURBULENT`.
The `CustomClusteredEngine` expects:
- `regime`: "QUIET", "NORMAL", "TURBULENT", "CRISIS" (Matches).
- `market_environment`: "EXPANSION", "INFLATIONARY_TREND", "STAGNATION", "CRISIS" (Matches Quadrant output).

We should pass both:
- `request.regime` <- `detector.detect_regime(...)` [0] (The label)
- `request.market_environment` <- `detector.detect_regime(...)` [2] (The quadrant)

### 3.3 Risk Profile Adaptations (Existing & New)

| Regime | L2 Gamma (Regularization) | Aggressor Allocation (Barbell) | New: Cash Buffer? |
| :--- | :--- | :--- | :--- |
| **QUIET** | 0.05 (Low) | 15% (High Alpha) | 0% |
| **NORMAL** | 0.05 | 10% | 0% |
| **TURBULENT** | 0.10 | 5% | 10% (Proposed) |
| **CRISIS** | 0.20 (High) | 3% (Defense) | 25% (Proposed) |

*Note: Cash buffer logic is not yet in `CustomClusteredEngine`. For v1, we focus on enabling the existing L2 and Aggressor adaptations.*

## 4. Test Plan (`tests/test_regime_risk_integration.py`)
1.  **Mock Context**: Create a `BacktestEngine` with mocked `MarketRegimeDetector`.
2.  **Scenario A (Normal)**: Detector returns "NORMAL". Check `EngineRequest` has `regime="NORMAL"`.
3.  **Scenario B (Crisis)**: Detector returns "CRISIS". Check `EngineRequest` has `regime="CRISIS"`.
4.  **Impact Test**: Run `CustomClusteredEngine` optimization with "CRISIS" vs "NORMAL" and assert `weights` are different (higher L2 should yield more diverse/damped weights).

## 5. Verification
- Run `flow-production` (or atomic run) and check logs for "Regime: CRISIS" etc.
- Verify `audit.jsonl` contains varying regimes.
