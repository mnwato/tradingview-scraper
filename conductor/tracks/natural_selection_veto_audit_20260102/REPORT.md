# Audit Report: Natural Selection Veto & ECI Scaling

## 1. Findings
- **Unit Mismatch**: The `futures` scanner often returns `Value.Traded = 0.0` for non-primary contracts or illiquid hours.
- **Numerical Blowup**: The ECI formula $\text{vol} \times \sqrt{\frac{1e6}{ADV}}$ was dividing by near-zero values, leading to ECI values in the millions.
- **Mass Vetoes**: All Futures/Forex assets were being vetoed because my metadata enrichment only applied fallbacks if the field was `None` or `NaN`, not `0.0`.

## 2. Remediation
- **Enrichment Fix**: Updated `enrich_candidates_metadata.py` to treat `value_traded <= 0.0` as missing, triggering the institutional floor (100M-1B USD).
- **Engine Guard**: Updated `NaturalSelectionEngine` to:
    1. Enforce a minimum ADV of 100M if data is missing.
    2. Cap the total `ECI` impact at 10% (0.10) to prevent numerical instability.
- **Validation**: Re-ran the selection stage. 21 candidates now survive, including multiple Futures (`COMEX:SIH2026`, `NYMEX:HPH2026`) and Forex (`THINKMARKETS:GBPJPY`) assets.

## 3. Residual Issues
- **Barbell Constraints**: The Barbell optimizer failed the logic audit due to a cluster constraint violation. This is outside the scope of the ECI audit and will be addressed in a future track.
