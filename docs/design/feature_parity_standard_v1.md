# Design: Feature Parity Standard (v1)

## 1. Objective
To establish a formal standard for the accuracy of replicated technical indicators, ensuring they are interchangeable with "fetched" data for ranking purposes.

## 2. Parity Envelope
A replicated rating is considered **PASS** if it meets the following criteria:

| Metric | Threshold | Rationale |
| :--- | :--- | :--- |
| **Mean Absolute Error (MAE)** | $< 0.05$ | Small enough to preserve relative rank order. |
| **Sign Accuracy** | $100\%$ | Directional bias (BUY/SELL) must always match. |
| **Pearson Correlation** | $> 0.98$ | Tight linear relationship over time. |

## 3. Ground Truth Data Sourcing

The `scripts/audit/audit_feature_parity.py` utility will:
1. Initialize the `Screener` API.
2. Query the `crypto` market for specific symbols.
3. Capture `Recommend.All`, `Recommend.MA`, and `Recommend.Other`.
4. Store the snapshot in `data/lakehouse/audit/feature_ground_truth.json`.

## 4. Remediation Tuning
If the parity audit fails the envelope, the following indicators will be tuned in `tradingview_scraper/utils/technicals.py`:
- **Ichimoku**: Check displacement and span intersection rules.
- **RSI**: Check smoothing method (Wilder's vs standard EMA).
- **Stochastic**: Check k/d period alignment.

## 5. Automation
Integrate `make feature-audit` into the development workflow to prevent logic regression during future technical utility updates.
