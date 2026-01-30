# Spec: End-to-End Pipeline Factor Audit

## 1. Goal
Ensure that technical indicators used in the **Discovery** stage (Scanners) are mathematically consistent with the **Natural Selection** engine (Log-MPS 3.2) and subsequent **Optimizer** stages. Prevent "Factor Drift" where early pruning uses criteria that contradict downstream alpha capture.

## 2. Key Objectives
- **Momentum Alignment**: Resolve the discrepancy between scanner-based trailing performance (`Perf.3M`) and selector-based window-local mean returns.
- **Volatility Alignment**: Align scanner filters (`Volatility.D`, `ATR`) with selector-based standard deviation and fragility scores.
- **Liquidity Standardization**: Ensure `Value.Traded` usage is consistent for both initial volume floors and downstream Estimated Cost of Implementation (ECI) calculations.
- **Darwinian Gate Review**: Audit the `eci_hurdle` and `kappa_threshold` to ensure they don't over-prune specific asset classes (e.g., highly volatile but high-alpha crypto).

## 3. Success Criteria
- Audit report documenting all "Factor Mismatch" gaps.
- Unified technical factor model applied across `configs/*.yaml` and `engines.py`.
- Validation benchmark confirming no high-alpha assets are lost in the early Discovery stage.
