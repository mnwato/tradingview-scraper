# Remediation Plan: Custom MPS Weights for MA Strategies (2026-01-16)

## 1. Problem Statement
The "Rating MA" strategies (`binance_spot_rating_ma_*`) are currently ranked using the default Global Log-MPS weights, where `momentum` (1.75) dominates `recommend_ma` (1.0). This dilutes the specific intent of the strategy, as the generic momentum factor overshadows the specific Moving Average Rating signal.

## 2. Solution: Profile-Specific Weight Overrides
We will introduce a mechanism to override specific MPS weights via the manifest's `features` block. This allows the MA profile to boost `recommend_ma` and suppress `momentum`, making the strategy self-contained.

## 3. Implementation Plan

### 3.1 Settings Update (`tradingview_scraper/settings.py`)
Add `mps_weights_override` dictionary to `FeatureFlags`.

### 3.2 Inference Engine Update (`tradingview_scraper/pipelines/inference/inference.py`)
Update `calculate_mps_score` (or the logic that loads weights) to merge the `mps_weights_override` on top of the global defaults.

### 3.3 Manifest Update (`configs/manifest.json`)
Update `binance_spot_rating_ma_short` (and Long) to:
```json
"features": {
  "mps_weights_override": {
    "momentum": 0.5,       // Suppress generic momentum
    "recommend_ma": 3.0    // Boost MA Rating
  }
}
```

## 4. Verification
- **Code Check**: Verify that `inference.py` correctly merges the weights.
- **Dry Run**: `make port-select PROFILE=binance_spot_rating_ma_short` and inspect `selection_audit.json` to see if scores have shifted (expect wider variance driven by MA rating).

## 5. Documentation
Update `universe_selection_v3.md` to document the `mps_weights_override` feature.
