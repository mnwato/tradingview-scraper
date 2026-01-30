# Spec: Natural Selection Veto & ECI Scaling Audit

## 1. Problem
The `Natural Selection (v3)` engine is vetoing nearly all Futures and Forex assets. The primary reasons appear to be:
1.  **Extreme ECI (Estimated Cost of Implementation)**: Vetoes like `High ECI (13124047.3536)` suggest a unit mismatch in `Value.Traded` or `ADV`.
2.  **Condition Number (\(\kappa\))**: High condition numbers in the correlation matrix trigger "Panic Mode," restricting clusters to 1 asset.

## 2. Objectives
- Audit `Value.Traded` units across all scanners (Crypto, Equity, Futures, Forex, CFD).
- Standardize the `ECI` formula to handle disparate liquidity profiles fairly.
- Review the `eci_hurdle` (0.5%) and ensure it doesn't penalize diversified beta unnecessarily.
- Implement a robust fallback for `ADV` when the scanner returns 0 or missing values.

## 3. Formulas under Review
- **ECI**: $volatility \times \sqrt{\frac{OrderSize}{ADV}}$
- **Condition Number**: $\kappa(\mathbf{C}) = \frac{\lambda_{max}}{\lambda_{min}}$ of the correlation matrix.
- **Veto Logic**: $Annualized\_Alpha - ECI < Hurdle$.
