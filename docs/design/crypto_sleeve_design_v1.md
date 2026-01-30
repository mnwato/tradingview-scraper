# Crypto Sleeve Design Document v3.3.1

## 1. Architecture Overview

### 1.1 System Context
The crypto sleeve operates as an independent capital allocation unit within the Fractal Risk Meta-Portfolio architecture, providing orthogonal exposure to digital assets while maintaining institutional-grade risk controls.

### 1.2 Design Principles
1. **Directional Normalization**: All returns are transformed to "Synthetic Longs" prior to analysis.
2. **Short-Cycle Momentum**: 10-day rebalancing window as the structural standard (Updated Jan 2026).
3. **Institutional Training Depth**: 252-day training windows ($T_{train}$) to capture full annual seasonality and regime cycles.
4. **Noise Floor Selection**: Late-binding trend filters to reject "dead-cat bounces."
5. **DataOps Hygiene**: Strict export isolation and automatic candidate consolidation (DataOps 2.0).
6. **HRP Dominance**: Hierarchical Risk Parity as the primary stability profile.
7. **Temporal Alignment**: Distance matrices averaged across 60d, 120d, and 200d windows.
8. **Deep Auditability**: Full matrix transparency via window-by-window forensic reports.
9. **Hard Asset Floor**: Mandatory 252-day history floor for all implementation candidates to ensure statistical robustness.

---

## 21. Refinement Funnel Architecture

### 21.1 Liquidity Normalization & The Discovery Funnel
A forensic audit of global crypto liquidity reveals that raw screener metrics (`Value.Traded`) are not USD-normalized across currency pairs. Local fiat pairs (IDR, TRY, ARS) can dominate the rank with local-currency denominated volume.

To ensure institutional signal quality, the Discovery Layer implements a **Six-Stage Refinement Funnel** (Updated Jan 2026):
1.  **Stage 1 (Discovery)**: Fetches up to 5000 candidates sorted by raw liquidity from verified CEXs. (Result: ~214 symbols).
2.  **Stage 2 (Normalization)**: Explicitly filters for institutional quote patterns (`USDT`, `USDC`, `FDUSD`) at the source. (Result: ~108 symbols).
3.  **Stage 3 (Consolidation)**: Aggregates disjoint scanner outputs (e.g., from parallel sharded scans) into a single master candidate ledger (`portfolio_candidates.json`), enforcing schema validity and removing rogue artifacts.
    - **Superset Strategy**: Allows mixed Long/Short pools to be ingested once (`data-ingest`) and consumed by multiple specialized pipelines (`flow-production`), preventing race conditions.
4.  **Stage 4 (Metadata Enrichment & Traceability)**: Injects institutional default execution metadata (`tick_size`, `lot_size`) for all candidates.
    - **Instrument Map**: During deduplication, if a PERP instrument (`BTC.P`) is discarded in favor of SPOT (`BTC`), its metadata MUST be preserved in an `alternatives` field within the SPOT candidate record. This enables the **Execution Router** to "hydrate" a Short trade with the correct PERP symbol at order generation time.
5.  **Stage 5 (Identity Deduplication)**: Removes redundant instruments (e.g. Spot vs Perp) for the same underlying asset. (Result: ~64 symbols).
    - **Canonical Selection**: Prefers SPOT for liquidity/data history, but links PERP as an execution alternative.
6.  **Stage 6 (Statistical Selection & Signal Dominance)**: Executes Selection v4 (Log-MPS/HTR) engine with:
    - **Pluggable Ranking**: Profiles can sort ascending/descending to handle monotonic signals (e.g., Rating MA Short).
    - **Signal Dominance**: Profiles can assert specific signals (e.g., `Recommend.MA`) to override generic momentum, boosting signal-to-noise ratio for specialized strategies.
    - **Outcome**: ~31 highly-qualified winners.

---

## 22. Discovery-Backtest Regime Mismatch & Historical Persistence (v3.6.5)

### 22.1 The Data Disconnect
A forensic audit reveals a structural limitation in backtesting Rating-based strategies (`binance_spot_rating_*`):
1.  **Discovery Phase**: Scanners filter for candidates using **current-time** signals (e.g., `Recommend.MA > 0` at $T_{now}$).
2.  **Backtest Phase**: The engine simulates historical performance using these "Today's Winners".
3.  **Rebalance Gap**: When rebalancing at historical time $T_{past}$, the selection engine lacks the point-in-time rating values for that date. It defaults to static logic or generic momentum, failing to replicate the strategy's true selection criteria.

### 22.2 Implications for Performance
Strategies like `Rating MA` appear to underperform because the backtest is evaluating "The historical drift of assets that are Buy-Rated *today*", rather than "The performance of buying Buy-Rated assets *historically*." This creates a Survivorship/Lookahead bias that distorts the Sharpe ratio.

### 22.3 Strategic Resolution: Historical Feature Persistence
To enable true backtesting, the platform mandates the transition to **Daily Feature Persistence**:
- **Requirement**: Capture and store scanner outputs (Ratings, Technicals) daily into the Lakehouse.
- **Goal**: Build a `features_matrix.parquet` alongside `returns_matrix.parquet`.
- **Policy**: Do **NOT** discard currently "low-performing" profiles (like `Rating MA`). Their poor backtest metrics are likely an artifact of data scarcity, not strategy failure. Keep them active to accumulate the necessary history for a valid future backtest.

---

## 23. Meta-Portfolio Fractal Architecture (v3.6.7)
The platform implements a hierarchical risk allocation framework known as the **Fractal Tree**. For detailed technical specifications, see [Fractal Hierarchical Meta-Portfolio Specification](../specs/fractal_meta_portfolio_v1.md).

### 23.1 Design Principles
1. **Recursive Nesting**: Meta-portfolios can contain other meta-portfolios as sleeves.
2. **Physical Flattening**: All strategic logic is eventually collapsed into net symbol exposures.
3. **Audit Integrity**: Unflattened cluster trees are preserved for forensic review.

---

## 24. Synthetic Signal Engine (v3.6.5)

### 24.1 Motivation
While "Daily Persistence" builds future history, we need a solution for *past* history to backtest strategies immediately. The **Synthetic Signal Engine** reconstructs TradingView ratings from raw OHLCV data.

### 24.2 Architecture
- **Library**: `pandas-ta` (Classic) for indicator calculation.
- **Logic**: Replicates the "Voting System" used by TradingView.
    - **MA Components**: SMA (10-200), EMA (10-200), Ichimoku, VWMA, HullMA.
    - **Oscillator Components**: RSI, Stoch, CCI, ADX, AO, Momentum, MACD, StochRSI, WillR, BBP, UO.
    - **Scoring**: $Score = \frac{\sum Votes}{N_{components}}$, where Vote $\in \{+1, -1\}$.
- **Validation**: The engine is calibrated against the daily `ingest_features` snapshot to ensure correlation > 0.9 before being trusted for historical backtesting.

---

## 25. Synthetic Long Normalization & Directional Purity (v3.3.0)
To ensure that all quantitative models (Selection, HRP, MVO) operate with maximum consistency across Long and Short regimes, the platform enforces **Synthetic Long Normalization**:

1.  **Late-Binding Direction**: At each rebalance boundary (production or backtest window), the system calculates the recent momentum ($M$) for all candidates.
2.  **Alpha Alignment**: The raw returns matrix ($R_{raw}$) is transformed into an alpha-aligned matrix ($R_{\alpha}$):
    - If $M > 0$, asset is **LONG**; $R_{\alpha} = R_{raw}$
    - If $M < 0$, asset is **SHORT**; $R_{\alpha} = -clip(R_{raw}, upper=1.0)$ (short loss cap at -100%)
3.  **Model Invariance**: Portfolio engines receive the $R_{\alpha}$ matrix. Because all assets now display positive expected returns, HRP and MVO models correctly reward stable price trends regardless of their physical direction. This eliminates the need for direction-aware code paths in the optimizers.
4.  **Forensic Replay**: The assigned direction and synthetic weights are recorded in the `audit.jsonl` ledger, enabling full reconstruction of the `Net_Weight` ($W_{net} = W_{synthetic} \times \text{sign}(M)$).

---

## 26. Deep Forensic reporting (v3.3.1)
To support institutional compliance and quantitative transparency, the system generates a **Deep Full Analysis & Audit Report**:
- **Funnel Trace**: Step-by-step retention metrics for the Five-Stage Funnel.
- **Risk Matrix**: Performance comparison across 153 engine/profile/simulator combinations.
- **Window Audit**: Trace of rebalance events, including assigned directions and top holdings.
- **Outlier Logic**: Automated Z-score identification of performance deviations.

---

**Version**: 3.6.7  
**Status**: Production Certified  
**Last Updated**: 2026-01-18
