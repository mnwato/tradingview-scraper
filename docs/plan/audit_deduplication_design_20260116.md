# Design Review & Audit Plan: Identity Deduplication (2026-01-16)

## 1. Context
The user has raised a strategic question regarding **Stage 5 (Identity Deduplication)**:
> "Should we keep SPOT and PERPS symbols for the same asset? or we will cluster them into one single cluster with hierarchical clustering, because PERPS would be used for shorting easily"

Current Architecture:
- **Discovery**: `binance_spot_rating_*` profiles explicitly filter for `type: spot`.
- **Deduplication**: `scripts/select_top_universe.py` enforces "Canonical Consolidation" (One Asset = One Instrument).
- **Selection**: `tradingview_scraper/pipelines/selection/stages/policy.py` enforces "Identity-Based Deduplication" to prevent intra-cluster collisions.

## 2. Analysis: Spot vs. Perp Coexistence

### 2.1 The Case for Separation (Current State)
- **Alpha Purity**: Mixing Spot and Perp introduces "Basis Risk" (Funding Rates) into the returns matrix. If optimization is driven by technicals (Rating), the underlying price action is 99% correlated.
- **Cluster Dilution**: Including both `BTC.SPOT` and `BTC.PERP` creates a massive cluster (Correlation ~1.0). HRP/ERC would split weight 50/50.
    - *Result*: Double transaction fees (2 trades) for identical beta exposure.
- **Execution Complexity**: Optimizers assume instruments are distinct assets. They don't know that `BTC.PERP` is just a derivative of `BTC.SPOT`.

### 2.2 The Case for Coexistence (User Proposition)
- **Shorting Efficiency**: Perps are natively shortable. Spot requires Margin (borrowing).
- **Regime Switching**:
    - **Bull Market**: Prefer Spot (No Funding Fees).
    - **Bear Market**: Prefer Perp (Easy Short).

### 2.3 Structural Blockers
The current `binance_spot_*` profiles operate on a `spot`-only universe definition. To support Perps, we would need:
1.  **New Profiles**: `binance_meta_*` (Mixed Universe).
2.  **Instrument-Aware Optimization**: The optimizer needs to know *why* it's picking Perp vs Spot.
    - If it picks both, it's inefficient.
    - It needs a "Preference Function" (e.g., if Net Weight < 0, swap to Perp).

## 3. Recommendation
**Keep Deduplication Active**.
Allowing duplicates into the *Selection/Optimization* engine causes numerical instability and cost inefficiency. The choice of Instrument (Spot vs Perp) is an **Execution Layer** decision, not an Alpha Selection decision.

**Proposed Architecture (Future)**:
1.  **Selection**: Select "Asset Identity" (e.g., `BTC`).
2.  **Allocation**: Allocate Weight to Identity (e.g., `-0.05`).
3.  **Execution Router**:
    - If `Weight > 0`: Buy Spot (or Perp if leverage needed).
    - If `Weight < 0`: Sell Perp (or Margin Short Spot).

## 4. Audit Plan (Verification of Current Behavior)
Verify that the current "Spot Only" profiles are indeed strictly enforcing Spot-only selection, ensuring no unintended Perp leakage.

### 4.1 Execution Steps
1.  **Check Discovery Configs**: Confirm `configs/scanners/crypto/ratings/*.yaml` exclude `.P` symbols.
2.  **Check Dedup Logic**: Review `scripts/select_top_universe.py` to confirm it effectively handles any leakages.
3.  **Audit Artifacts**: Inspect `portfolio_candidates.json` from `prod_short_all_v2` to confirm zero perps.

## 5. Deliverable
- Audit Report confirming system integrity.
- Design Decision Record (DDR) strictly defining Deduplication as an Alpha-Layer invariant.
