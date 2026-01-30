# Implementation Plan: Entropy & Predictability Research
**Track ID**: `entropy_predictability_research_20251221`
**Status**: Planned

## 1. Objective
Quantify the predictability of market segments using Information Theory. This track aims to identify "Low Entropy" opportunities where the signal is mathematically distinguishable from random uncertainty.

## 2. Phases

### Phase 1: Complexity Audit
Goal: Calculate entropy metrics for the Top 200 universe.
- [ ] Task: Implement **Shannon Entropy** (distributional randomness) and **Permutation Entropy** (temporal order).
- [ ] Task: Correlate Entropy scores with Strategy Success (e.g., does Trend-Following perform better on low-entropy assets?).
- [ ] Task: Research **Approximate Entropy (ApEn)** for small data windows.

### Phase 2: Uncertainty Mapping
Goal: Detect market regimes where uncertainty is high.
- [ ] Task: Build an "Entropy Heatmap" across exchanges and asset classes.
- [ ] Task: Identify "Predictability Decay" – how quickly an asset transitions from ordered to random.

### Phase 3: Integration
- [ ] Task: Create an `EntropyFilter` for the `FuturesUniverseSelector` to discard "Maximum Uncertainty" symbols.
- [ ] Task: Final Report.
