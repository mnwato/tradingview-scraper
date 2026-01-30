# Implementation Plan: Alternative Technical Indicators & Detailed Analysis Research

## Phase 1: Comprehensive Field Discovery [checkpoint: cc1d65f]
Goal: Identify all pre-calculated indicators available via the `scanner.tradingview.com/symbol` API.

- [x] Task: Research and list "Oscillators" versus "Moving Averages" summaries provided by TradingView.
- [x] Task: Document specific fields for advanced indicators not in the default list (e.g., Ichimoku, Hull MA, Pivot Points).
- [x] Task: Verify the availability of "Rating" fields (e.g., `Recommend.MA`, `Recommend.Other`) for granular decision making.
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Validation of Data Depth & Timeframes [checkpoint: cc1d65f]
Goal: Ensure pre-calculated indicators align with institutional research needs across all resolutions.

- [x] Task: Research and validate indicator availability for ultra-low timeframes (1m, 5m) via the Scanner API.
- [x] Task: Compare the "Scanner Snapshot" indicators against "recalculated" values from OHLCV to verify precision.
- [x] Task: Document any "Missing Data" edge cases for low-liquidity or newly listed assets.
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Prototyping the "Institutional Tech Details" Page [checkpoint: cc1d65f]
Goal: Build a prototype that aggregates all pre-calculated metrics into a high-density report.

- [x] Task: Create `scripts/generate_tech_report.py` to fetch and format 20+ indicators for a specific symbol.
- [x] Task: Design a "Consensus Engine" that weighs different indicator categories (e.g., Oscillators vs MAs).
- [x] Task: Final Report: Is the pre-calculated API robust enough to replace local recalculation for high-res analysis?
- [x] Task: Conductor - User Manual Verification 'Phase 3'