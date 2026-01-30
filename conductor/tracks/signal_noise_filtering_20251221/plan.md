# Implementation Plan: Signal/Noise Based Filtering
**Track ID**: `signal_noise_filtering_20251221`
**Status**: Planned

## 1. Objective
Improve strategy hit rates by isolating high-signal trends from market noise. This track focuses on the Signal-to-Noise Ratio (SNR) and the mathematical "efficiency" of price moves.

## 2. Phases

### Phase 1: Noise Identification
Goal: Quantify the level of "Chop" in the current universe.
- [ ] Task: Implement the **Hurst Exponent** to distinguish trending markets from random walks.
- [ ] Task: Implement **Kaufman's Efficiency Ratio (ER)**: (Net Change / Total Path).
- [ ] Task: Build a "Noise Profile" for each major exchange.

### Phase 2: SNR Alpha Filters
Goal: Filter signals based on trend quality.
- [ ] Task: Implement a **Kalman Filter** or **Wiener Filter** prototype to smooth noise in real-time scans.
- [ ] Task: Rank signals by "Signal Intensity" (SNR) rather than just raw performance.

### Phase 3: Validation
- [ ] Task: Backtest the "Filtered vs Unfiltered" signal lists.
- [ ] Task: Integrate SNR weights into the Barbell Optimizer.
- [ ] Task: Final Report.
