# Design: Rating Logic Tuning (v1)

## 1. Objective
To achieve numerical parity (MAE < 0.05) between the replicated technical ratings (`TechnicalRatings`) and the ground truth from TradingView, specifically addressing the divergence in `Recommend.MA`.

## 2. Tuning Targets

### 2.1 Ichimoku Logic Pivot
- **Current Issue**: Divergence in `Recommend.MA` due to incorrect Ichimoku component.
- **New Logic**: The 15th component of the Moving Averages rating is the **Ichimoku Base Line (Kijun-sen)**, not the Cloud.
- **Formula**:
  - `BaseLine` = (Highest High + Lowest Low) / 2 over 26 periods.
  - `Buy` if `Close > BaseLine`.
  - `Sell` if `Close < BaseLine`.
  - `Neutral` otherwise.

### 2.2 Component Alignment (The 15 Votes)
The `Recommend.MA` rating is the average of 15 votes:
1.  **SMA 10, 20, 30, 50, 100, 200** (6 votes)
2.  **EMA 10, 20, 30, 50, 100, 200** (6 votes)
3.  **Hull MA 9** (1 vote)
4.  **VWMA 20** (1 vote)
5.  **Ichimoku Base Line (26)** (1 vote)

### 2.3 Reference Preservation
- **`technicals_v0.py`**: The original scalar implementation (from commit `3b89074`) will be restored to serve as a regression baseline.

## 3. Iterative Tuning Process
1.  **Baseline**: Run `audit_feature_parity.py` to get current MAE.
2.  **Experiment**: Modify `TechnicalRatings` logic (one indicator at a time).
3.  **Validate**: Re-run audit script.
4.  **Repeat**: Until MAE < 0.05.

## 4. TDD Strategy
- **`tests/test_rating_tuning.py`**:
    - Focus on specific indicator alignment (e.g., `test_ichimoku_displacement`).
    - Use manually verified "micro-ground-truth" points.
