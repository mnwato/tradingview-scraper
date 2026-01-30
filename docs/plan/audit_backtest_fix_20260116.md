# Backtest Audit Plan (2026-01-16)

## 1. Objective
Validate that the recent fixes to `backtest_engine.py` resolve the missing metadata, turnover calculation, and HHI reporting issues.

## 2. Issues Addressed
1.  **Missing Context**: `Train/Test/Step` parameters were missing from `tournament_results.json`.
2.  **NaN Vol-HHI**: `top_assets` was stripped during sanitization, preventing HHI calculation.
3.  **Turnover N/A**: Simulators were re-initialized every window, breaking turnover continuity.

## 3. Verification Strategy
We will execute a lightweight "Smoke Test" of the `flow-production` pipeline using the `development` profile to generate artifacts quickly.

### 3.1 Execution Command
```bash
make flow-production PROFILE=development RUN_ID=audit_fix_test_v1
```

### 3.2 Audit Steps
1.  **Check `tournament_results.json`**:
    - Verify `meta` key exists and contains `train_window`, `test_window`, `step_size`.
    - Verify `results` entries contain `top_assets` in their metrics.
    - Verify `concentration_hhi` is present in metrics.
2.  **Check Reports**:
    - Generate report: `scripts/production/generate_deep_report.py audit_fix_test_v1`
    - Inspect `comparison.md` to ensure "Backtest Context" table is populated.
    - Inspect "Risk Fidelity Audit" table to ensure `Vol-HHI Corr` is numeric (not NaN).
3.  **Check Turnover**:
    - Verify turnover metrics are non-constant (i.e., not always 0.5 or 1.0).

## 4. Rollback
If validation fails, revert changes to `scripts/backtest_engine.py`.
