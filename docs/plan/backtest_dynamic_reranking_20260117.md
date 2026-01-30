# Plan: Backtesting with Dynamic Re-Ranking (2026-01-17)

## 1. Objective
Enable the Backtest Engine to re-rank portfolio candidates dynamically at each rebalance window using reconstructed historical ratings (`Recommend.All`, `Recommend.MA`). This resolves the "Lookahead Bias" where backtests relied on the *current* rating of assets selected today.

## 2. Architecture

### 2.1 Historical Feature Store
We need a `features_matrix.parquet` (Index: Date, Columns: Multi-Index [Symbol, Feature]) alongside the existing `returns_matrix.parquet`.
Since we don't have this yet, we must **synthesize** it on the fly using the `TechnicalRatings` utility and the raw OHLCV data.

### 2.2 Backtest Strategy Update (`scripts/backtest_engine.py`)
Modify the `BacktestEngine` or `ReturnsSimulator` to accept a `feature_loader` callback.

**Logic Flow**:
1.  **Rebalance Step (T)**:
    - Get the pool of available assets (Universe).
    - Load OHLCV history for these assets up to T.
    - Calculate `Recommend.MA` / `Recommend.All` using `TechnicalRatings` for each asset at T.
    - **Re-Rank**: Sort assets by this reconstructed score (Ascending/Descending based on profile).
    - **Select**: Pick Top-N.
    - **Optimize**: Run Mean-Variance/HRP on the selected subset.

### 2.3 Challenges
- **Performance**: Calculating indicators for ~200 assets at every rebalance step (e.g., 90 steps) is computationally expensive (`pandas-ta` overhead).
- **Optimization**: Pre-calculate the entire `features_matrix` *before* the backtest loop starts.

## 3. Implementation Plan

### 3.1 Pre-Calculation Service (`scripts/services/backfill_features.py`)
Create a service that:
1.  Iterates over all assets in `portfolio_candidates.json`.
2.  Loads their full OHLCV history.
3.  Calculates `Recommend.MA` and `Recommend.Other` time-series for the entire history.
4.  Saves a consolidated `features_matrix.parquet` (Time x Asset x Feature).

### 3.2 Backtest Integration
Update `scripts/backtest_engine.py` to:
1.  Load `features_matrix.parquet` if available.
2.  In the rebalance loop, look up the rating at time T from the matrix (O(1) lookup).
3.  Filter/Rank based on this historical value.

## 4. Execution Steps
1.  **Build Backfill Script**: `scripts/services/backfill_features.py`.
2.  **Generate Matrix**: Run backfill for the current universe.
3.  **Update Backtest Engine**: Inject `historical_features` logic.
4.  **Rerun Production**: `prod_ma_short_v4` with true historical ranking.

## 5. Deliverables
- `scripts/services/backfill_features.py`
- `features_matrix.parquet` (Artifact)
- Updated `backtest_engine.py`
