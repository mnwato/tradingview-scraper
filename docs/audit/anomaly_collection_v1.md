# Audit: Anomaly Collection & Forensic Outliers (v1)

## 1. Objective
To catalog and analyze the numerical anomalies and forensic outliers identified during the production validation run (`meta_production_20260123-005221`).

## 2. Collected Anomalies

### 2.1 Numerical Explosion (Annualized Return > 1000%)
- **Window 60, `max_sharpe`, `crypto_all`**: Annualized Return = **10000.00%**.
- **Root Cause**: Likely a near-zero variance in a single asset combined with a high-conviction signal, leading the optimizer to allocate extreme leverage in the "Synthetic long" stream.
- **Impact**: Distorts meta-portfolio performance and indicates mathematical instability in the `max_sharpe` solver.

### 2.2 Return Clipping Artifacts (-99.99%)
- **Window 30, `max_sharpe`, `crypto_all`**: Annualized Return = **-99.99%**.
- **Root Cause**: Negative returns exceeded the safety floor. This indicates that the 500% daily cap is insufficient to prevent catastrophic drawdowns in high-volatility regimes if rebalancing is too frequent or solvers are over-aggressive.

### 2.3 Weight Leakage (Stable Sum Gate Warnings)
- **Warning**: `Meta Sum=1.0000, Atomic Sum=1.9365`
- **Warning**: `Meta Sum=1.0000, Atomic Sum=0.9682`
- **Root Cause**: 
  - Overlap in physical assets across sleeves without proper deduplication in some paths.
  - Inconsistent handling of logic-atom suffixes (`_trend`, `_meanrev`) during physical collapse.

### 2.4 Trace Linkage Gaps
- **Observation**: "Forensic trace missing" in report header.
- **Root Cause**: The report generator looks for `forensic_trace.json` in the parent directory but it may have been nested differently or flush failed during the Ray shutdown.

## 3. Prioritized Suggestions

1.  **Stricter Return Bounds**: Lower daily cap to 100% (1.0) for standard solvers; keep 500% only for "toxic data" detection.
2.  **Solvency Check**: Add a rule to `BacktestEngine`: if $W_{sum} \approx 0$ or $W_{std} > 10$, force Equal Weight.
3.  **Contributor Metadata Fix**: Repair `flatten_meta_weights.py` to ensure `Contributors` list is correctly populated and not shadowed by recursive calls.
4.  **Trace Path Standardization**: Use `settings.run_dir` for all telemetry artifacts to ensure the reporter always finds the trace.
