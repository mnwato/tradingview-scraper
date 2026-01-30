# Specification: Predictability Feature Flags

## 1. Overview
This track introduces feature flags and configurable thresholds for the spectral predictability filters (Entropy, Hurst, Efficiency Ratio) implemented in the Natural Selection stage. This allows for gradual rollout, A/B testing, and fine-tuning without code changes.

## 2. Functional Requirements

### 2.1 Feature Flags
- Add `feat_predictability_vetoes` (default: `False`) to `FeatureFlags`.
- Add `feat_efficiency_scoring` (default: `False`) to `FeatureFlags`.

### 2.2 Configurable Thresholds
Add the following configurable parameters to `FeatureFlags` or `TradingViewScraperSettings`:
- `entropy_max_threshold`: Default `0.9`.
- `efficiency_min_threshold`: Default `0.1`.
- `hurst_random_walk_min`: Default `0.45`.
- `hurst_random_walk_max`: Default `0.55`.

### 2.3 Selection Engine Integration
- Update `SelectionEngineV3` core logic to:
    - Only apply "Predictability Vetoes" if `feat_predictability_vetoes` is `True`.
    - Only include "efficiency" in MPS scoring if `feat_efficiency_scoring` is `True`.
    - Use the new configurable thresholds instead of hardcoded values.

## 3. Non-Functional Requirements
- **Defaults**: By default, the new filters should be disabled to maintain backward compatibility with existing production profiles until explicitly enabled in the manifest.

## 4. Acceptance Criteria
- `FeatureFlags` model is updated.
- `SelectionEngineV3` respects the new flags and thresholds.
- Unit tests verify that toggling the flags enables/disables the filters.
- Audit logs correctly report that filters were skipped if flags are disabled.
