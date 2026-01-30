# Design: Regime Survival Calendar (Darwinian Gate)

## 1. Objective
To disqualify "Fragile" assets that have not been tested by market stress or regime transitions.

## 2. Defined Stress Windows (The "Extinction Events")
| Event ID | Period | Description | Asset Class Impact |
| :--- | :--- | :--- | :--- |
| `CRISIS_2022_Q2` | 2022-05-01 to 2022-06-30 | UST/LUNA Collapse / Inflation Spike | Crypto, Growth Stocks |
| `CRISIS_2023_Q1` | 2023-03-01 to 2023-03-31 | Regional Banking Crisis (SVB) | Small Caps, Financials |
| `CRISIS_2024_AUG` | 2024-08-01 to 2024-08-10 | Yen Carry Trade Unwind | Global Beta, Carry Pairs |

## 3. Scoring Logic
For each window $W_i$:
1.  **Presence Check**: Are there < 2% missing bars in $W_i$?
2.  **Volatility Check**: Did the asset maintain a bid/ask spread (or volume) within $2\sigma$ of its pre-crisis mean?
3.  **Survival Result**: `Binary_Gate = (Success_Count / Total_Windows) >= 0.66`

## 4. Implementation
- Store windows in `configs/legacy/stress_calendar.yaml` (legacy preset location).
- Update `audit_antifragility.py` to calculate `Regime_Survival_Score`.
