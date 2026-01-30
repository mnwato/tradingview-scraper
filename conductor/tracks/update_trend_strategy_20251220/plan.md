# Implementation Plan: Update Trend Following Strategy Universe Selectors

## Phase 1: Core Preset Infrastructure & Standard Update [checkpoint: d7ae1ba]
Goal: Align all 34 trend-following presets with the new base universe standards.

- [x] Task: Audit and group all 34 trend-following YAML files into manageable batches. ca925cd
- [x] Task: Update Binance trend presets (Long/Short, Spot/Perp) with $1M VT floor and aggregation. a69c8e5
- [x] Task: Update Bybit/OKX/Bitget trend presets with $500k VT floor and aggregation. a69c8e5
- [x] Task: Standardize 'limit: 50' and 'exclude_dated_futures: true' across all batches. a69c8e5
- [x] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md) ca925cd

## Phase 2: Execution & Strategy Output Quality Verification [checkpoint: d7ae1ba]
Goal: Run the updated scanners and verify that the resulting universes are accurate and high-quality.

- [x] Task: Run all updated trend-following scanners using existing shell infrastructure. ca925cd
- [x] Task: Verify that strategy outputs contain 0 dated futures. ca925cd
- [x] Task: Validate that 'Value.Traded' in strategy results correctly reflects summed liquidity. ca925cd
- [x] Task: Execute 'verify_universe_quality.py' on strategy outputs to ensure uniqueness and compliance. ca925cd
- [x] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md) ca925cd

## Phase 3: Documentation & Final Integration [checkpoint: d7ae1ba]
Goal: Finalize the track with updated summaries and clean artifacts.

- [x] Task: Update project documentation (README or universe spec) to reflect new institutional trend limits. ca925cd
- [x] Task: Generate a final aggregation matrix for the trend strategy run. ca925cd
- [x] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md) ca925cd
