# Plan: Quadrant-Aware Adaptive Optimization

**Status**: Planned
**Date**: 2026-01-01
**Goal**: Implement an autonomous engine that switches portfolio optimization profiles based on the detected All Weather quadrant.

## 1. Task: Define Adaptive Mapping Standard
Establish the "Gold Standard" mapping between market environments and risk profiles.

| Quadrant | Environment | Recommended Profile | Rationale |
| :--- | :--- | :--- | :--- |
| **EXPANSION** | High Growth / Low Stress | `max_sharpe` | Maximize returns in stable bullish regimes. |
| **INFLATIONARY_TREND** | High Growth / High Stress | `barbell` | Protect core while chasing volatile alpha. |
| **STAGNATION** | Low Growth / Low Stress | `min_variance` | Minimize cost/vol when opportunity is scarce. |
| **CRISIS** | Low Growth / High Stress | `hrp` | Prioritize structural survival and tail hedging. |

## 2. Task: Implement `RegimeAdaptiveEngine`
Develop a meta-engine in `tradingview_scraper/portfolio_engines/engines.py` that delegates logic based on real-time detection.

- **Action**: Create `RegimeAdaptiveEngine(BaseRiskEngine)`.
- **Logic**: 
    1. Call `MarketRegimeDetector.detect_quadrant_regime()`.
    2. Map quadrant to profile using the mapping standard.
    3. Forward the `EngineRequest` to the appropriate underlying logic.
- **Transparency**: Record the "Profile Switch" decision in the engine's metadata for the audit ledger.

## 3. Task: Tournament Integration
Enable the `adaptive` profile as a first-class citizen in the tournament matrix.

- **Action**: Update `BacktestEngine.run_tournament` to support the `adaptive` profile.
- **Goal**: Compare `adaptive | cvxportfolio` against static profiles (e.g., `max_sharpe | cvxportfolio`) to quantify the "Regime Alpha."

## 4. Task: Enhanced Reporting
Update the reporting engine to visualize profile transitions.

- **Action**: Modify `ReportGenerator` to extract the `selected_profile` from the audit ledger.
- **Visualization**: Generate a timeline showing which profile was active in each 20-day window.

## 5. Success Criteria
- **Outperformance**: The `adaptive` profile should achieve a higher overall Sharpe than any single static profile over a full 1-year walk-forward test.
- **Stability**: The engine should not "thrash" between profiles (verified via the transition timeline).
- **Auditability**: Every profile switch is cryptographically signed and recorded in `audit.jsonl`.
