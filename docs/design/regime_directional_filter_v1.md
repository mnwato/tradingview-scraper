# Design Specification: Regime Directional Filter Research (v1.0)

## 1. Objective
Investigate the efficacy of the `MarketRegimeDetector` (specifically the 'Quadrant' and 'Regime Score') as a directional filter for portfolio allocation. The goal is to determine if we can systematically:
- **Confirm Longs**: When Regime is EXPANSION or INFLATIONARY_TREND.
- **Confirm Shorts**: When Regime is CRISIS or DEFLATION.
- **Avoid Trade**: When Regime is STAGNATION (or conflicting).

## 2. Hypothesis
- **H1 (Crisis Confirmation)**: Assets in `CRISIS` regime (Score > 1.8 or Quadrant=CRISIS) have a negative expected return over the next 10 days.
- **H2 (Trend Confirmation)**: Assets in `INFLATIONARY_TREND` or `EXPANSION` have a positive expected return.
- **H3 (Quiet Danger)**: `QUIET` regime might be mean-reverting or low-volatility drift, but sensitive to shocks.

## 3. Methodology

### 3.1 Data Source
- Use `data/lakehouse/features_matrix.parquet` (if it contains price data? No, it contains features). 
- Use `data/lakehouse/returns_matrix.parquet` (Daily Returns).
- We need price or cumulative returns to calculate forward returns accurately. Or simply rolling sum of daily returns.

### 3.2 Metrics
- **Forward Return (FwdRet_N)**: Rolling sum of returns from T+1 to T+N.
- **Conditional Expectation**: $E[FwdRet | Regime]$.
- **Win Rate**: $P(FwdRet > 0 | Regime)$.

### 3.3 Research Script (`scripts/research/research_regime_direction.py`)
1.  **Load Data**: Load `returns_matrix.parquet`.
2.  **Rolling Regime Detection**:
    - Iterate through time (or vectorise if possible, but Regime Detector uses 64-day windows).
    - Calculating full spectral turbulence on rolling windows is expensive.
    - **Optimization**: Use a stride (e.g., every 5 days) or a subset of assets (e.g., top 10 liquid) to verify the hypothesis first. Or use `BTC` and `ETH` as proxies for the crypto market.
3.  **Analysis**:
    - Tag each day with (Regime, Score, Quadrant).
    - Align with T+5, T+10, T+20 returns.
    - Aggregate statistics.
4.  **Output**: Markdown report with tables.

## 4. TDD Strategy (`tests/test_regime_direction.py`)
- **Mock Data**: Create synthetic price series with known trends.
- **Test**: Verify that the "Research Logic" correctly aligns T's Regime with T+N's Return.
    - If at T=100, Regime is detected, we look at returns from 101 to 110.
    - Ensure no lookahead bias in the research script itself.

## 5. Success Criteria
- Validated script that produces a clear "Signal Efficacy" report.
- Determination of whether `Regime` should be added as a hard constraint in the `BacktestEngine`.
