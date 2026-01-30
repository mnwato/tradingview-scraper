# Design: Tail-Risk Hardening & Anomaly Remediation (v1)

## 1. Objective
To mitigate mathematical instabilities and forensic data gaps identified during the production validation phase.

## 2. Numerical Dampening

### 2.1 Return Clipping (Lowered Threshold)
The `ReturnScalingGuard` will be tightened to prevent 10000% annualized artifacts.
- **New Bound**: $|r_{daily}| \le 1.0$ (100% daily return cap).
- **Reasoning**: Any daily return > 100% is statistically suspicious and likely indicates a data error or a "flash crash" artifact that corrupts mean-variance optimizers.

### 2.2 Volatility Floor
Implement a minimum variance floor in `BacktestEngine` before covariance calculation.
- **Rule**: $\sigma_{min} = 1 \times 10^{-6}$.
- **Action**: Add white noise to assets with zero variance to prevent singular matrices.

## 3. Stability Gates

### 3.1 Adaptive Window Veto
If a backtest window produces a Sharpe ratio $|S| > 10$, the engine will:
1. Attempt **Adaptive Ridge Reloading** (already implemented).
2. If it remains $> 10$ after 3 retries: **Veto the window** and force Equal Weight.
3. Record a `ForensicAnomaly` event in the audit ledger.

## 4. Contributor Attribution Repair
Fix the bug in `flatten_meta_weights.py` where the `Contributors` list was not correctly passed during physical asset summation.

- **Fix**: Use a `Set` to track `sleeve_id` for each `physical_symbol` and serialize as a sorted list.

## 5. Telemetry Path Standardization
Standardize the location of `forensic_trace.json` to ensure the report generator can always locate it.

- **Target**: `QuantSDK.run_pipeline` will write to `settings.run_dir / "forensic_trace.json"`.
- **Target**: `generate_meta_report.py` will resolve trace via `settings.run_dir`.
