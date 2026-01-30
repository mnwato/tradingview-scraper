# Review Plan: Risk Profiles Matrix Audit (2026-01-16)

## 1. Objective
Audit the generated performance reports for the certified Q1 2026 production runs to construct a consolidated **Risk Profiles Matrix**. This matrix will compare the realized risk/return characteristics across different strategy profiles (Long/Short, Ratings/MA).

## 2. Target Runs
- **Run A**: `prod_long_all_v2` (Binance Spot Rating All - Long)
- **Run B**: `prod_short_all_v2` (Binance Spot Rating All - Short)
- **Run C**: `prod_ma_long_v2` (Binance Spot Rating MA - Long)
- **Run D**: `prod_ma_short_v2` (Binance Spot Rating MA - Short)

## 3. Execution Steps

### 3.1 Artifact Verification
Confirm existence of `comparison.md` reports for all target runs.

### 3.2 Data Extraction
For each run, extract the following metrics for the top-performing engine/simulator combination:
- **Max Sharpe Profile**: Sharpe, Volatility, MaxDD, CAGR.
- **Min Variance Profile**: Sharpe, Volatility, MaxDD, CAGR.
- **Equal Weight Profile**: Sharpe, Volatility, MaxDD, CAGR.

### 3.3 Matrix Construction
Synthesize the extracted data into a unified table.

## 4. Output
A consolidated "Risk Profiles Matrix" report.
