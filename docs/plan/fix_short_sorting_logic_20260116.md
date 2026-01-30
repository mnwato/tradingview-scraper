# Remediation Plan: Short Sorting Logic Fix (2026-01-16)

## 1. Objective
Fix the logic inversion in `tradingview_scraper/pipelines/selection/stages/policy.py` to ensure that Short candidates are ranked by the **strength of their bearish signal**, not the weakness of it.

## 2. Theoretical Alignment
- **Long Profiles**: Rank Descending (Highest Score = Strongest Bull).
- **Short Profiles**: Rank Ascending (Lowest Score = Strongest Bear).
    - *Assumption*: The underlying Alpha Score (Log-MPS) is positively correlated with price momentum/rating.

## 3. Implementation Plan

### 3.1 Code Modification
**File**: `tradingview_scraper/pipelines/selection/stages/policy.py`
**Action**: Locate the `select` method (or equivalent) where `shorts` are sorted.
**Change**:
```python
# Check if profile/direction implies "Short"
if direction == "SHORT":
    # Sort Ascending (Lowest Score First) -> Prioritize Deepest Bears
    ranked_shorts = sorted(shorts, key=_get_score, reverse=False)
else:
    # Sort Descending (Highest Score First) -> Prioritize Strongest Bulls
    ranked_shorts = sorted(shorts, key=_get_score, reverse=True)
```

### 3.2 Verification
We must verify that this change improves the "MA Short" profile without breaking the "Rating All Short" profile.
- **Hypothesis**: "Rating All" might use a different score distribution. If "Rating All" scores are inverted (High Score = Bearish), this fix would break it.
- **Check**: Review `inference.py` or the `selection_audit.json` from `prod_short_all_v2` to confirm the score-to-signal relationship for that specific logic.

## 4. Execution
1.  Apply the fix to `policy.py`.
2.  Rerun `prod_ma_short_v2` (or a smoke test version).
3.  Compare "Winners" list: Does it now include `XPLUSDT` (Deep Bear) instead of `DOTUSDT` (Flat)?

## 5. Rollback
If the fix degrades `prod_short_all_v2`, we must implement logic-specific sorting (e.g., `if logic == 'rating_ma': reverse=False`).
