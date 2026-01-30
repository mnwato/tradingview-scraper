# Forex MTF Strategy: Secular Trend Alignment

The Forex Multi-Timeframe (MTF) strategy is designed to identify "Overall Long" opportunities in the G8 Major currencies by requiring structural alignment across Monthly, Weekly, and Daily horizons.

## 1. Strategy Architecture

The strategy uses a "Waterfall Filter" to ensure we are trading with the secular wind at our back:

### Tier 1: Monthly Anchor (The Trend)
- **Goal**: Identify multi-year secular bull regimes.
- **Filters**: 
    - **ADX > 15** (Strong structural trend).
    - **6-Month Performance > 0.0%**.
    - **Recommendation Score > 0.1**.

### Tier 2: Weekly Confirmation (The Support)
- **Goal**: Ensure the medium-term momentum is aligned with the secular trend.
- **Filters**:
    - **ADX > 12**.
    - **1-Month Performance > 0.2%**.

### Tier 3: Daily Execution (The Timing)
- **Goal**: Filter for immediate positive price action and entry timing.
- **Filters**:
    - **Price > SMA20**.
    - **Weekly Change > 0.0%**.

## 2. Universe Definition (G8 Majors)

The universe is strictly restricted to the primary crosses of the global reserve and major industrial currencies:
`USD, EUR, JPY, GBP, AUD, CAD, CHF, NZD`

## 3. Risk Mitigation via Clustering

Forex pairs are inherently correlated due to shared denominators (e.g., being "Long USD" via `EURUSD`, `GBPUSD`, and `AUDUSD` simultaneously). 

To prevent unintentional over-leveraging into a single currency factor:
1.  **Hierarchical Analysis**: All MTF candidates are grouped into risk buckets.
2.  **Cluster Concentration Cap**: The entire "USD-Denominator Cluster" is capped at **25%** total weight in the portfolio.
3.  **Lead Asset Preference**: The system selects the pair within the cluster that offers the best **Volatility-to-ADX** ratio for execution.
