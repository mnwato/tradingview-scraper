# Remediation Plan: Optimization Hardening (2026-01-17)

## 1. Issue Overview
During the Meta-Portfolio generation, it was observed that certain sleeves failed to produce specific risk profiles:
- **Sleeve**: `long_ma` (Run: `prod_ma_long_v3`) -> Missing `hrp`, `barbell`.
- **Sleeve**: `short_all` (Run: `prod_short_all_v3`) -> Missing `hrp`.

Current status: **Mitigated** via "Best Effort Proxy" (MinVar fallback).
Target status: **Resolved** (All profiles generated natively).

## 2. Investigation Plan

### 2.1 Audit Solver Logs
- **Action**: Inspect `artifacts/summaries/runs/prod_ma_long_v3/logs/11_optimization.log` specifically for `HRP` and `CVXPortfolio` errors.
- **Hypothesis**: The `long_ma` universe might be too small or too correlated, causing the `HRP` recursive bisection to fail or `CVXPortfolio` to find the problem infeasible under strict constraints.

### 2.2 Configuration Review
- Check `configs/manifest.json` for `binance_spot_rating_ma_long`.
- Verify if `backtest.profiles` includes `hrp` and `barbell`. (It appears to, based on manifest inspection).

## 3. Fix Schedule

| ID | Task | Component | Priority | ETA |
| :--- | :--- | :--- | :--- | :--- |
| **FIX-001** | Relax Solver Constraints | `optimize_clustered_v2.py` | Medium | Q2 Sprint 1 |
| **FIX-002** | HRP Robustness | `portfolio_engines/risk_parity.py` | Medium | Q2 Sprint 1 |
| **FIX-003** | Rerun Base Sleeves | Production Pipeline | Low | Q2 Sprint 1 |
| **FIX-004** | Fix Metric RuntimeWarnings | `utils/metrics.py` | Medium | Q2 Sprint 1 |

## 4. Immediate Action
No immediate re-run is required as the Proxy Fallback provided a valid, mathematically similar return stream for the Meta-Portfolio.
