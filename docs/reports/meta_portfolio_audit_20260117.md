# Meta-Portfolio Audit Report (2026-01-17)

## 1. Executive Summary
**Status**: ✅ **Functionally Valid**, ⚠️ **Performance Critical**.
The Meta-Portfolio pipeline successfully aggregated 4 diverse sleeves (`long_all`, `short_all`, `long_ma`, `short_ma`) into unified "Meta-Profiles" (Barbell, HRP, MinVar). The allocation logic and fallback mechanisms worked as designed.

However, the **Realized Performance** of these meta-portfolios is extremely poor (Sharpe < -1.0, MaxDD > -100%), primarily driven by:
1.  **Short Sleeve Toxicity**: The `short_ma` and `short_all` sleeves have massive negative returns (bull market regime), dragging down the aggregate.
2.  **Allocation Limits**: The Meta-Allocation floor (`min_weight: 0.05`) forces capital into these losing short sleeves, preventing the optimizer from fully rotating into the profitable Long sleeves.

## 2. Meta-Profile Analysis

| Meta-Profile | Allocation Strategy | Sharpe | MaxDD | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Barbell** | 90% Long / 10% Short | **-1.55** | **-103%** | Failed (Short Drag) |
| **MinVariance** | 25% Equal Allocation | **-1.06** | **-344%** | Failed (Forced Diversification) |
| **HRP** | 25% Equal Allocation | **-2.38** | **-1857%** | Failed (Volatility Explosion) |

## 3. Root Cause: Forced Diversification
The `manifest.json` configuration for `meta_super_benchmark` enforces:
```json
"meta_allocation": {
  "min_weight": 0.05,
  "max_weight": 0.5
}
```
In a strong bull market, *any* forced allocation to shorts (5%) without perfect timing results in significant drag. When combined with leverage (implied by volatility > 100%), this leads to bankruptcy scenarios.

## 4. Remediation Plan (Phase 219+)
1.  **Dynamic Meta-Constraints**: Allow `min_weight` to drop to 0.0 during strong trend regimes (Regime-Aware Meta-Allocation).
2.  **Short Veto**: Use the `RegimeDetector` to disable Short sleeves entirely in "INFLATIONARY_TREND" or "EXPANSION" regimes.
3.  **Historical Fidelity**: The "Discovery-Backtest Regime Mismatch" (Phase 219) is critical. Current backtests on "Today's Losers" (for shorts) might be picking assets that *already crashed*, meaning we are shorting at the bottom. True historical rating reconstruction will likely improve short selection.

## 5. Conclusion
The infrastructure works perfectly. The strategy configuration needs tuning for regime alignment.
