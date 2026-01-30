# Audit Report: Crypto Discovery Factor Alignment

## 1. Executive Summary
This audit resolved significant "Factor Drift" between the discovery scanners and the Natural Selection engine. By standardizing the liquidity floor to $10M and synchronizing momentum horizons to 1M/3M, we have ensured that the candidate pool entering the optimizer is pre-filtered for institutional tradability and statistical trend strength.

## 2. Key Findings
- **Liquidity Mismatch**: Previous configs used floors as low as $1.5M, while the Selection Engine expected a $10M institutional baseline for full probability scoring.
- **Redundancy**: Configuration files were highly repetitive, making global updates (like changing an exchange priority) difficult and error-prone.
- **Momentum Drift**: Scanners were using varying horizons (e.g., `change`, `Perf.W`), whereas the downstream engine focuses on secular trends.

## 3. Improvements
- **Preserved Survival**: The standardized $10M floor ensures that only assets with sufficient depth for institutional-sized orders ($1M+) enter the backtest.
- **Reduced Noise**: Raising the volatility ceiling to 35% allows for crypto-native alpha while pruning extreme outliers that cause correlation matrix instability (Kappa threshold triggers).
- **Architecture**: Moved from "Fat Configs" to "Lean Strategy Overlays" via the new 3-layer inheritance model:
    1.  `base_crypto_spot.yaml` (Universal Factors)
    2.  `base_binance_spot.yaml` (Exchange Constraints)
    3.  `crypto_cex_trend_binance_spot_long.yaml` (Strategy Logic)

## 4. Validation Results
- **Binance Spot Dry-Run**: Verified that `Value.Traded > 10,000,000` is correctly injected into the payload.
- **Binance Perp Dry-Run**: Verified that `include_perps_only: true` and `prefer_perps: true` are inherited and correctly serialized.
- **Base Scan Integrity**: Verified that `trend` filters are correctly nulled in base scans, preserving the full top-N universe for audit purposes.
