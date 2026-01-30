# Design Specification: Dynamic Historical Backtesting & Synthetic Backfill (v1.1)

## 1. Objective
Enable the platform to perform high-fidelity backtesting of Rating-based strategies by reconstructing historical technical features (`Recommend.All`, `Recommend.MA`, etc.) from raw OHLCV data. This resolves the "Discovery-Backtest Regime Mismatch" where scanners currently only provide current-time signals.

## 2. Architecture

### 2.1 The Historical Feature Store
A new artifact, `features_matrix.parquet`, will be generated alongside `returns_matrix.parquet`.
- **Index**: DateTime (UTC).
- **Structure**: Wide-format DataFrame where columns are `Symbol` (assuming single feature `rating_score` for MVP) or MultiIndex if multiple features needed.
- **Storage**: Run-specific data directory (`data/summaries/runs/<RUN_ID>/data/features_matrix.parquet`).

### 2.2 Synthetic Backfill Service (`scripts/services/backfill_features.py`)
A service that leverages `pandas-ta` (or custom vectorized logic) to generate time-series signals.

**Rating Logic (Simplified TV Standard)**:
- **Moving Averages (0.5 to 1.0 = Buy)**:
    - Price > SMA(20), Price > SMA(50), Price > SMA(200)
    - EMA(20) > SMA(20) (Trend)
- **Oscillators (-1.0 to 1.0)**:
    - RSI(14) < 30 (Oversold/Buy), > 70 (Overbought/Sell)
    - MACD Line > Signal Line (Buy)
- **Composite Score**: Mean of MA Score and Oscillator Score.

### 2.3 Dynamic Backtest Integration
The `BacktestEngine` will be updated to:
1. Load the `features_matrix.parquet`.
2. At each rebalance window $T$:
    - Retrieve the cross-sectional slice of features for all active symbols.
    - **Re-Rank** the candidates: Filter out those with Rating < Threshold (e.g. 0.0 for Neutral, 0.5 for Strong Buy).
    - Select Top N based on Rating/Momentum.
    - Hand off the selected subset to the optimization solvers.

## 3. Implementation Plan

### Step 1: Feature Backfill Service (`scripts/services/backfill_features.py`)
- **Input**: `portfolio_candidates.json` (for universe), Lakehouse OHLCV Parquet files.
- **Process**:
    - Iterate over unique symbols.
    - Load full history.
    - Compute Vectorized Indicators.
    - Aggregate into a normalized `rating` (-1 to 1).
    - Store column in Matrix.
- **Output**: `features_matrix.parquet`.

### Step 2: Backtest Engine Refactoring (`scripts/backtest_engine.py`)
- Add `features_path` argument.
- In `rebalance()` loop:
    - `current_ratings = features_matrix.loc[date]`
    - `valid_candidates = current_ratings[current_ratings > threshold].index`
    - Use this `valid_candidates` list to mask the covariance matrix and returns.

### Step 3: Pipeline Integration
- Add `Feature Backfill` as a standard step in the `port-pre-opt` or just before `port-test`?
- *Decision*: Ideally before `port-optimize` so optimization also sees the filtered universe?
    - Actually, `port-optimize` is a "Solver" step. `Natural Selection` usually happens before.
    - However, `Natural Selection` is currently static.
    - **Dynamic Selection** happens inside the Backtest Loop (for simulation) or inside the Solver (if solver supports dynamic constraints).
    - For `BacktestEngine` (Simulation), we simulate the *historical decision making*.
    - So `Backfill` must happen *before* `port-test`.

## 4. Success Criteria
- `features_matrix.parquet` exists and contains valid ratings for all symbols.
- Backtest rebalances show dynamic symbol rotation.
- `audit.json` logs show different asset selections at different rebalance dates.
