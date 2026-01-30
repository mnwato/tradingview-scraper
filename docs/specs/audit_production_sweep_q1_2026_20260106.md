# Audit: Full Production Sweep Q1 2026 (Run 20260106-prod-q1)

This audit documents the execution and validation of the first institutional-grade production tournament for Q1 2026.

## 1. Execution Summary
- **Run ID**: `20260106-prod-q1`
- **History Depth**: 500 Days (Secular)
- **Windowing**: `180/40/20` (Stability Default)
- **Universe**: 19 Selected Symbols (Equities + Commodities + Crypto)
- **Status**: ✅ Completed & Validated

## 2. Pipeline Stage Analysis

### 2.1 Discovery & Aggregation
- **Scanners**: 11 scanners executed.
- **Top Sources**: `sp500_alpha_trend` (21), `binance_alpha_trend` (21), `commodity_proxy_etfs` (7).
- **Raw Pool**: 50 unique symbols.

### 2.2 Natural Selection & Enrichment
- **Winners**: 19 symbols passed the momentum + alpha + metadata coverage gates.
- **Enrichment**: 100% metadata coverage achieved for selected candidates.

### 2.3 Data Integrity
- **Health**: 100% gap-free data for the secular lookback.
- **Repair**: 0 gaps required filling for the final 19-symbol universe.

### 2.4 Optimization & Regime
- **Regime**: Detected **QUIET** (Score: 0.69) recently, allowing for convex profiles.
- **Clustering**: 19 clusters generated; HRP exercised with sufficient breadth.

### 2.5 Tournament & Scoreboard
- **Fidelity**: `friction_decay` aligned across simulators (~0.08).
- **Candidates**: 4 Strict Candidates emerged (Non-Baseline).
- **Auto-Calibration**: `max_temporal_fragility` calibrated to 7.31 based on historical baseline variance.

#### 2.6 Winner Forensics: Riskfolio Barbell
The `riskfolio/barbell` configuration swept the tournament, passing strict gates across all 4 simulators (`custom`, `nautilus`, `vectorbt`, `cvxportfolio`).

| Metric | Value | Note |
| :--- | :--- | :--- |
| **Avg Window Sharpe** | **4.09** | Exceptional performance driven by QUIET regime leverage. |
| **Annualized Return** | **37.0%** | Strong alpha capture. |
| **Max Drawdown** | **-2.6%** | Very low drawdown indicating defensive stability. |
| **Turnover** | **48.0%** | Efficient execution (below 50% gate). |
| **Temporal Fragility** | **0.67** | Highly stable (well below 1.50 limit). |
| **Parity Gap** | **0.48%** | Excellent alignment between CVXPortfolio and Nautilus. |

**Regime Context**: The recent 20-day regime was identified as **QUIET** (Score: 0.69), which favors convex strategies like Barbell that can aggressively capture upside while maintaining a hedged core.

## 3. Final Verification
- **Ledger Integrity**: Cryptographic hash chain verified via `verify_ledger.py` (100% VALID).
- **Artifacts**: All reports, tearsheets, and returns pickles persisted in the run directory.

## 4. Next Steps
- Promote the 4 top candidates to the order-generation pipeline.
- Continue quarterly guardrail sentinel monitoring.
