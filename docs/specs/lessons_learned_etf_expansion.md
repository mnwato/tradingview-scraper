# Lessons Learned: ETF Expansion & Adaptive Selection (Jan 2026)

## 1. The "Liquid Winners" Discovery Pattern
**Problem**: Traditional scanners that filter by `Return > X` often return illiquid penny stocks, while scanners that filter by `Volume > Y` often return low-alpha giants. The intersection is frequently empty or noisy.

**Solution**: **Split-Layer Filtering**.
1.  **Layer 1 (API)**: Sort by `Value.Traded` (Liquidity) to fetch the top 300 tradeable assets. *Do not filter by performance here.*
2.  **Layer 2 (Client)**: Apply strict Alpha gates (`Perf.1M > 0`) and Hygiene gates (`Volatility < 4%`) to this liquid pool.
3.  **Layer 3 (Ranking)**: Sort the survivors by Alpha (`Perf` or `Yield`).

**Outcome**: We successfully discovered high-alpha institutional assets like `RKLX` ($33M Vol, +127% Return) that were previously missed by static lists or naive filters.

## 2. Adaptive Engine vs. Static Profiles
**Finding**: The **Adaptive Meta-Engine** (Sharpe 2.65) outperformed all static profiles (MinVar, HRP, MaxSharpe) in the Q1 2026 Tournament.

**Mechanism**:
-   **Regime Detection**: Accurately labeled windows as `QUIET` (Bull) or `TURBULENT` (Choppy).
-   **Dynamic Switching**:
    -   **Bull**: Switched to `max_sharpe` (Aggressive), capturing upside (e.g., `URA`, `KOLD`).
    -   **Turbulent**: Switched to `hrp` (Defensive), pivoting to `LQD`, `HYG`, `GLD`.

**Decision**: While `adaptive` is superior, we kept `skfolio` (Barbell) as the default for the `institutional_etf` profile to ensure predictable, stable baselines for daily reporting. `adaptive` is reserved for "High Octane" mandates.

## 3. "Cluster Battles" in Selection V3
**Observation**: The Hierarchical Clustering logic (`Ward` linkage) effectively enforces "One Bet Per Factor".

**Evidence**:
-   **Silver Cluster**: `SLV` (Anchor) consistently defeated `AGQ` (2x Leveraged) due to the Stability component of the LogMPS score.
-   **Gold Cluster**: `GLD` defeated `IAU` and `SGOL` due to superior Liquidity scoring.

**Implication**: The system naturally creates "Core" portfolios. To create "Barbell" portfolios (Core + Satellite), we rely on the Optimizer (Barbell Profile) to explicitly force Aggressor weights, rather than hoping Selection keeps them.

## 4. Metadata Integrity
**Success**: We validated the availability of critical fields (`aum`, `expense_ratio`, `dividend_yield_recent`) across the entire ETF universe.
**Action**: These are now standard columns in all `tradfi` scanners, enabling future "Smart Beta" filters (e.g., "Yield > 4% AND Expense < 0.20%").

## 5. Extreme Momentum Discovery
**Problem**: Can the system safely handle "Meme" or "Parabolic" assets without blowing up the risk model?

**Finding**: The "Liquid Winners" architecture successfully identified **`CBOE:ASTX`** (Tradr 2X Long ASTS) with a **+300% 1M Return** and ADX of 27.0.
-   **Handling**:
    -   **Discovery**: Caught by `etf_thematic_momentum` scanner ($2M+ floor).
    -   **Selection**: Passed filters but flagged as high volatility.
    -   **Optimization**: The `Barbell` profile allocated exactly **2.00%** (Aggressor Cap) to it.
-   **Lesson**: The system correctly treats extreme momentum as a "Satellite" bet, capping the downside while exposing the portfolio to the convexity.

