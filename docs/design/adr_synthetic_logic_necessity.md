# Architectural Decision Record: Necessity of Synthetic Logic in Meta-Portfolio Era

## Context
With the introduction of **Meta-Portfolios** (Phase 159/184), which act as a global hierarchical risk management layer aggregating multiple component profiles (Long/Short, Trend/MeanRev), we re-evaluated the necessity of the lower-level **Synthetic Logic Symbols** (e.g., `BTC_rating_ma_long_SHORT`).

## Decision
We confirm that **Synthetic Logic Symbols are Mandatory** and cannot be deprecated.

## Rationale

### 1. The Solver's "Rising Equity" Requirement
Optimization engines (Markowitz, HRP, MinVar) are fundamentally designed to maximize risk-adjusted returns based on input history.
- **Problem**: If we feed raw `BTC` returns (which are rising) to a "Short Sleeve" optimizer, the optimizer will *buy* `BTC` because it has positive drift. It has no concept that the sleeve's mandate is "Short Only".
- **Solution**: We must **invert** the return stream *before* the optimizer sees it ($R_{syn,short} = -clip(R_{raw}, upper=1.0)$). This creates a "Synthetic Asset" that rises when the physical asset falls, while enforcing the -100% short loss cap for extreme moves. The optimizer then naturally allocates capital to this synthetic asset during downtrends, aligning mathematical optimization with the sleeve's strategic intent.

### 2. Sleeve-Internal Optimization
The Meta-Portfolio optimizes allocations *between* sleeves (e.g., 50% Long / 50% Short), but it relies on the Component Sleeves to be internally efficient.
- To create an efficient "Short Sleeve", the component optimizer needs to select the *best* shorts (those dropping the fastest with lowest volatility).
- This is only possible if the input data represents the PnL of the short position (i.e., the inverted return).

### 3. Identity & Granularity
A single physical asset (e.g., `ETH`) can simultaneously belong to multiple conflicting strategies:
- `ETH_Trend_Long`: Buy because 200d MA is positive.
- `ETH_MeanRev_Short`: Short because RSI is 80.
If we dropped the synthetic layer, we would conflate these distinct alpha signals into a single physical `ETH` return stream, destroying the ability to hedge specific factor risks.

## Implication
The architecture remains:
1.  **Data Layer**: Physical Returns (Truth).
2.  **Synthesis Layer**: Logical Inversion & Bankruptcy Guards (Interface).
3.  **Component Layer**: Optimize Synthetic Streams.
4.  **Meta Layer**: Aggregate Component Portfolios.
5.  **Execution Layer**: Flatten back to Net Physical Exposure.
