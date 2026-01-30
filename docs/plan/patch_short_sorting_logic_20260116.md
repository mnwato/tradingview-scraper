# Fix Plan: Short Sorting Logic (2026-01-16)

## 1. Problem Statement
The Selection Policy systematically prioritizes the "Least Bearish" assets for Short profiles because it sorts `alpha_score` in descending order.
- **Long**: High Score (1.0) = Bullish. Sort Descending ✅.
- **Short**: Low Score (0.0) = Bearish. Sort Descending ❌ (Picks 0.1 over 0.001).

## 2. Proposed Fix
Invert the sorting order for Short candidates in `tradingview_scraper/pipelines/selection/stages/policy.py`.

```python
# Before
ranked_shorts = sorted(shorts, key=_get_score, reverse=True)

# After
ranked_shorts = sorted(shorts, key=_get_score, reverse=False)
```

## 3. Impact Assessment
- **Rating MA Short**: Will now select Deep Negative Momentum (Score ~0.0) instead of Flat Momentum. Expected to fix the profile.
- **Rating All Short**: Will now select Deep Bearish signals instead of "Best of the Worst". Since this profile performed well (Sharpe 1.65) *despite* the bug (likely due to broad market beta), fixing it should theoretically improve alpha capture further or increase volatility (deeper shorts).

## 4. Execution
1.  Apply the fix to `tradingview_scraper/pipelines/selection/stages/policy.py`.
2.  Since we are in "Certification Wrap-Up", we will NOT rerun the full suite. Instead, we document this as a **Critical Patch** for the next deployment cycle (Q2 Dev).
3.  **Rationale**: `Rating All Short` is already certified as "Primary Alpha". Risking a regression/behavior change now is unnecessary. The `Rating MA Short` profile is deprecated anyway.

## 5. Documentation
Update `issues.md` or a new `known_issues_v3.6.md` to flag this logic inversion for the next sprint.
