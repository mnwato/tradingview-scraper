# Audit Plan: Recommand.All Signal Composition (2026-01-17)

## 1. Objective
Investigate how `Recommend.All` (Composite Rating) is derived and whether it incorporates `Recommend.MA` and `Recommend.Other` (Oscillators) in a way that aligns with our Alpha Scoring logic.

## 2. Hypothesis
`Recommend.All` is a linear combination of `Recommend.MA` and `Recommend.Other`.
Formula: `All = W_ma * MA + W_osc * Other`.
We need to determine the weights `W_ma` and `W_osc`.

## 3. Execution Steps

### 3.1 Data Inspection
Load the newly generated MTF features parquet file (`data/lakehouse/features/tv_technicals_1d/date=.../*.parquet`).

### 3.2 Correlation Analysis
Calculate the correlation between:
- `recommend_all_1d` vs `recommend_ma_1d`
- `recommend_all_1d` vs `recommend_other_1d`

### 3.3 Regression Analysis
Perform a simple linear regression to find the coefficients:
`All ~ c1 * MA + c2 * Other`

### 3.4 Review Logic
If `Recommend.All` is indeed a composite, determining the weights helps us understand if "Rating All" profiles are momentum-biased (high MA weight) or mean-reversion-biased (high Oscillator weight).

## 4. Deliverable
- An "Audit Report" detailing the composition of the TradingView Composite Rating.
