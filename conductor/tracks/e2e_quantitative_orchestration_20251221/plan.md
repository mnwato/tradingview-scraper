# Implementation Plan: E2E Quantitative Orchestration & Robust Risk
**Track ID**: `e2e_quantitative_orchestration_20251221`
**Status**: Planned

## 1. Objective
Consolidate the multi-asset quantitative pipeline into a unified, high-performance Python orchestrator and enhance the risk management layer with market-regime intelligence and Bayesian shrinkage.

## 2. Phases

### Phase 1: Unified Orchestrator & Async Discovery [checkpoint: 5d2cdba]
Goal: Transition from shell-based batching to a Python-native async architecture.
- [x] Task: Create `tradingview_scraper/pipeline.py` (Unified Orchestrator Class). 24bdb00
- [x] Task: Implement `AsyncScreener` to parallelize REST calls to TradingView. e7f267f
- [x] Task: Migrate existing configurations to be driven by the new `Pipeline` entry point. 8340c68

### Phase 2: Robust Risk & Regime Intelligence
Goal: Improve optimizer stability and adaptive capabilities.
- [x] Task: Implement `MarketRegimeDetector` (Volatility-based switch). 945e843
- [x] Task: Integrate **Ledoit-Wolf Shrinkage** for covariance estimation. 62c4076
- [x] Task: Update the Barbell Optimizer to adjust its "Safe Core" vs "Aggressor" split based on detected regimes. c618e48

### Phase 3: Scaling & Final Validation [checkpoint: 81fdd29]
Goal: Execute across the full universe and finalize the V1 architecture.
- [x] Task: Execute full E2E run for Top 200 symbols (Crypto + Global). ee2ee43
- [x] Task: Author the `Quantitative Workflow V1` final documentation. ee2ee43
