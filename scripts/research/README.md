# Research Scripts

This directory contains research and validation scripts used to reverse-engineer TradingView's technical rating logic (`Recommend.MA`, `Recommend.Other`, `Recommend.All`) and other experimental analysis tools.

## Scripts

### 1. `reconstruct_recommend_ma.py`
**Purpose**: Reconstructs the `Recommend.MA` (Moving Averages Rating) signal from raw OHLCV data using `pandas-ta`.
**Methodology**:
- Calculates 15 components:
    - SMA (10, 20, 30, 50, 100, 200)
    - EMA (10, 20, 30, 50, 100, 200)
    - Hull MA (9)
    - VWMA (20)
    - Ichimoku Cloud (Price vs Cloud at T-26)
- Logic: Buy (+1) if Price > MA, Sell (-1) if Price < MA.
- Verifies against daily feature snapshots.

### 2. `reconstruct_recommend_other.py`
**Purpose**: Reconstructs the `Recommend.Other` (Oscillators Rating) signal.
**Methodology**:
- Calculates 11 components:
    - RSI, Stochastic, CCI, ADX, AO, Momentum, MACD, StochRSI, Williams %R, Bull Bear Power, Ultimate Oscillator.
- **Refined Logic (Validated 2026-01-17)**:
    - **Stoch**: Sell if K > 80 AND K < D (Cross Down). Buy if K < 20 AND K > D (Cross Up).
    - **AO/BBP**: Buy if Positive AND Rising. Sell if Negative AND Falling.
- Verifies against daily feature snapshots.

### 3. `audit_recommend_all.py`
**Purpose**: Determines the weighting of `MA` and `Other` in the composite `Recommend.All` rating.
**Methodology**:
- Loads ingested feature snapshots.
- Performs Linear Regression: `All ~ c1 * MA + c2 * Other`.
- **Result (2026-01-17)**: `All ≈ 0.57 * MA + 0.39 * Other`.

## Usage
Run with `uv run` to ensure dependencies (pandas-ta-classic) are available.

```bash
uv run scripts/research/reconstruct_recommend_ma.py
uv run scripts/research/reconstruct_recommend_other.py
uv run scripts/research/audit_recommend_all.py
```
