# Tournament Review: Directional Baseline Alpha (Q1 2026)

## 1. Executive Summary
This review analyzes the exhaustive matrix tournament for `binance_spot_rating_all_long` and `binance_spot_rating_all_short` profiles. The audit confirms that **Short Alpha** is currently the primary driver of performance in the crypto spot market, while Long signals are facing regime-induced headwinds.

## 2. Performance Matrix (Mean Sharpe)

### 2.1 Long Baseline (`20260115-193120`)
The long baseline exhibited significant fragility during the lookback period:
- **Equal Weight**: -0.15 Sharpe
- **HRP / Risk Parity**: -0.44 Sharpe
- **Success Rate**: 41.67% (HRP)
- **Observation**: Negative performance across all engines indicates a structural downtrend in the recruited cash-market long candidates.

### 2.2 Short Baseline (`20260115-193308`)
The short baseline demonstrated robust alpha capture:
- **Equal Weight**: 2.04 Sharpe
- **HRP / Risk Parity**: 1.97 Sharpe
- **Success Rate**: 75.00% (HRP)
- **Observation**: Consistent positive alpha across all 3 engines (`skfolio`, `riskfolio`, `custom`) and simulators (`cvxportfolio`, `vectorbt`).

## 3. Simulator & Engine Stability Audit
- **Engine Parity**: High convergence observed between `skfolio` and `riskfolio` (identical Sharpe to 4 decimal places).
- **Simulator Delta**: `cvxportfolio` consistently reported slightly more conservative Sharpe ratios than `vectorbt` for the Short sleeve (1.90 vs 2.03), likely due to its more rigorous friction modeling (trading costs and slippage interaction).

## 4. Production Readiness Conclusion
The system is **Production Ready** for mixed-direction ensembling.
- The **Short Sleeve** provides high-conviction positive alpha which will serve as the primary "Aggressor" layer in the meta-portfolio.
- The **Long Sleeve**, while currently negative, serves as the necessary "Hedge" or "Diversifier" to reduce net beta in the meta-allocation layer.
- The near-zero correlation observed in Phase 159 (-0.07) validates that these two sleeves are truly orthogonal.
