# Deep Forensic Audit Plan: HRP Crash & Sorting Logic (2026-01-16)

## 1. Objective
Investigate two specific failure modes identified in the `prod_ma_short_v2` forensic analysis:
1.  **HRP Crash**: Determine the exact window and asset combination that caused the "Non-finite distance matrix" error.
2.  **Ranking Logic**: Verify if the "Short" profile correctly ranked candidates in **ascending** order (picking the *worst* rated assets for shorting), or if it mistakenly picked the *best* rated assets (descending).

## 2. Target Run
- **Run ID**: `prod_ma_short_v2`

## 3. Execution Steps

### 3.1 Ranking Verification
- **Code Review**: Check `tradingview_scraper/pipelines/selection/stages/logic.py` (or similar) to see how `sort_direction` or `ascending` is handled for Short profiles.
- **Data Review**: Inspect `selection_audit.json` again.
    - Look at the `alpha_score` of the winners.
    - If Strategy is SHORT, we expect Low/Negative scores (if score = rating) or High Negative scores.
    - If the scores are High Positive (e.g. 0.9), we are shorting the Bullish assets!

### 3.2 HRP Crash Localization
- **Log Scrape**: grep the logs for the exact window index where HRP failed.
- **Data Inspection**: Load the `returns_matrix.parquet` for that specific window and compute the correlation matrix manually.
    - Check for `NaN` correlations (assets with constant price? or zero overlap?).

## 4. Deliverable
- A "Deep Dive" report confirming whether we had a **Logic Bug** (Wrong Sort Order) or just **Toxic Data**.
