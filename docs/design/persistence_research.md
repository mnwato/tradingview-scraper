# Design: Persistence Research Engine

## Overview
The Persistence Research Engine is a pre-selection filter that evaluates the structural longevity of price behavior. It acts as a bridge between "Discovery" and "Natural Selection".

## Components

### 1. Predictability Extension
Location: `tradingview_scraper/utils/predictability.py`
New Responsibilities:
- Numerical solver for OU process parameters.
- Temporal counters for trend consistency.
- **Serial Correlation Profiling**: Analysis of autocorrelation lags to detect momentum memory and reversion speed.

### 2. Analysis Orchestrator
Location: `scripts/research/analyze_persistence.py`
Workflow:
1. Load Returns Matrix (aligned).
2. Reconstruct Price Path (using `np.cumprod(1 + returns)`).
3. Batch process assets using `ThreadPoolExecutor`.
4. Generate persistence classification:
   - `STRONG_TREND`: High Hurst (>0.55) + Positive AC Lag-1.
   - `STRONG_MR`: Low Hurst (<0.45) + Negative AC Lag-1.
   - `TRANSITIONAL`: High Hurst + Low Duration.
   - `REVERTING_CORE`: Low Hurst + Fast Half-Life.
   - `NOISY`: Hurst ~ 0.5 or AC insignificance.

## Integration Points
- **Makefile**: `make research-persistence` target.
- **Manifest**: Respects `TV_LOOKBACK_DAYS`.
- **Natural Selection**: Future potential to use `persistence_score` as a multiplicative factor.
