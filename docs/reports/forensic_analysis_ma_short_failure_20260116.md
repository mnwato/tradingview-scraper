# Forensic Analysis Report: `prod_ma_short_v2` Failure (2026-01-16)

## 1. Executive Summary
**Verdict**: **Strategy Failure (Alpha Decay)**, not Data Quality.
The "Rating MA Short" strategy selected 22 valid candidates with robust alpha scores, but the realized performance was negative (-0.39 Sharpe). The primary HRP optimizer crashed due to numerical instability (NaN correlation distance), but the MinVariance fallback succeeded, proving the data pipeline was functional.

## 2. Evidence of System Health
- **Selection**: 22 winners selected (e.g., `TONUSDT`, `AVAXUSDT`).
- **Data Integrity**: MinVariance optimizer successfully allocated weights, proving returns data was available.
- **Backtest Fidelity**: System correctly caught the HRP crash and continued execution.

## 3. Root Cause Analysis
### 3.1 HRP Instability
- **Error**: `The condensed distance matrix must contain only finite values.`
- **Cause**: In the "Short MA" universe, assets are highly correlated (all crashing together) or extremely volatile (gaps). This creates a singular covariance matrix, causing HRP's distance calculation ($d = \sqrt{2(1-\rho)}$) to fail if $\rho \approx 1.0$ or if gaps cause NaN correlations.

### 3.2 Alpha Decay
- **Observation**: Even with a successful MinVariance allocation, the strategy lost money (-8.6% MaxDD).
- **Conclusion**: The "Moving Average Rating" signal is likely **lagging**. By the time the MA flips bearish, the crash has already happened, and the 10-day rebalance forces the portfolio to short at the bottom (selling low) and cover higher (buying high).

## 4. Recommendation
**Deprecate `Rating MA` for Crypto**.
The 10-day rebalancing cycle requires faster signals (like the "Rating All" oscillator/trend composite). MA signals are too slow for the volatile crypto market structure.

**Action**: Move `prod_ma_short_v2` to the "Retired" archive and focus resources on the high-performing `prod_short_all_v2` (Sharpe 1.65).
