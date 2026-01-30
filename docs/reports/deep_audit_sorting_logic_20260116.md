# Deep Forensic Audit: HRP Crash & Sorting Logic (2026-01-16)

## 1. Executive Summary
**Status**: 🔴 **CRITICAL DEFECT DETECTED**
The forensic audit confirmed a logic inversion in the **Selection Policy** for Short profiles. The system is currently shorting the "Least Bearish" assets (highest scores) instead of the "Most Bearish" assets (lowest scores).

- **Ranking Logic**: Confirmed `reverse=True` (Descending) sort for Short candidates.
- **Score Logic**: Confirmed `alpha_score` scales with Momentum (High Score = High Momentum).
- **Outcome**: The strategy picks assets with Momentum $\approx 0$ (Flat/Mild Bear) instead of Momentum $\ll 0$ (Crash/Strong Bear). This explains the poor performance and the "HRP Crash" (shorting flat assets leads to zero-variance clusters).

## 2. Root Cause Analysis

### 2.1 The "Best of the Worst" Fallacy
The intention of the `binance_spot_rating_ma_short` profile is to find assets with **negative** ratings.
- The `inference.py` engine assigns low probabilities (e.g., $10^{-10}$) to strongly bearish assets and higher probabilities (e.g., $10^{-4}$) to mildly bearish assets.
- The `policy.py` sorts DESCENDING.
- **Result**: It picks the $10^{-4}$ assets (Mild Bear) and discards the $10^{-10}$ assets (Strong Bear).

### 2.2 The HRP Crash
- **Window**: 480
- **Cause**: By selecting "Mildly Bearish" assets, the portfolio is populated with low-volatility, range-bound assets.
- **Mechanism**:
    1.  Asset prices are effectively constant (low vol).
    2.  Returns $\approx 0$.
    3.  Variance $\approx 0$.
    4.  Correlation Matrix contains `NaN` (division by zero std dev) or Singularities.
    5.  HRP Distance Calculation fails: `The condensed distance matrix must contain only finite values.`

## 3. Remediation Plan

### 3.1 Code Fix
In `tradingview_scraper/pipelines/selection/stages/policy.py`, invert the sort order for Short candidates:
```python
# Before
ranked_shorts = sorted(shorts, key=_get_score, reverse=True)

# After
ranked_shorts = sorted(shorts, key=_get_score, reverse=False)
```

### 3.2 Verification
Rerun `prod_ma_short_v2` with the fix. We expect:
1.  Selection of "Toxic" (High Negative Momentum) assets.
2.  Higher volatility in the Short portfolio.
3.  Positive Alpha (profiting from crashes).
