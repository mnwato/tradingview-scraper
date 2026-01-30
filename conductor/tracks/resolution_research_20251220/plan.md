# Implementation Plan: Historical Candle Resolution & Depth Mapping

## Phase 1: Standard Resolution Audit [checkpoint: cdd13bb]
Goal: Formally document the existing supported resolutions and their lookback depths.

- [x] Task: Audit `tradingview_scraper/symbols/stream/streamer.py` for current timeframe mapping.
- [x] Task: Research depth limits for each standard interval (1m to 1M) for a major pair (`BTCUSDT`).
- [x] Task: Document the mapping between user-friendly strings (e.g., '1h') and internal API codes (e.g., '60').
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Non-Standard & High-Res Discovery [checkpoint: cdd13bb]
Goal: Experiment with unlisted or advanced resolutions (Seconds, Ticks, Custom Minutes).

- [x] Task: Research availability of Second-level resolutions (1S, 5S, 15S, 30S) via raw WebSocket experimentation (Confirmed: Not available on free tier).
- [x] Task: Research availability of "Custom Minutes" (e.g., 2m, 3m, 45m, 12h) (Found 3m, 45m, 3h are supported).
- [x] Task: Document the "Auth Requirement" for ultra-high-res data (Does 1S require a paid Pro/Premium JWT?).
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Comprehensive Resolution Matrix [checkpoint: cdd13bb]
Goal: Deliver a definitive resolution guide for the project.

- [x] Task: Create `docs/research/resolution_matrix_20251220.md` with verified depths and internal codes.
- [x] Task: Propose updates to the `DataLoader` to support discovered resolutions.
- [x] Task: Final Report: Feasibility of high-frequency strategy research using these resolutions.
- [x] Task: Conductor - User Manual Verification 'Phase 3'