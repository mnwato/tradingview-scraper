# Implementation Plan: Multi-Timeframe Technical Filtering for Trend Candidates

## Phase 1: Candidate Ingestion & MTF Mapping [checkpoint: 9155a18]
Goal: Systematically ingest initial trend signals and map the required MTF indicator set.

- [x] Task: Research automated ingestion of `export/<run_id>/universe_selector_binance_*_long/short_*.json` results.
- [x] Task: Define the "High-Conviction" MTF set (e.g., RSI, EMA, ADX across 15m, 1h, 4h, 1d).
- [x] Task: Document the naming schema for MTF keys (e.g., `BTCUSDT_15m_RSI`).
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: MTF Indicator Acquisition & Synchronization [checkpoint: 9155a18]
Goal: Efficiently fetch and synchronize technical snapshots across multiple timeframes.

- [x] Task: Research batch fetching of MTF indicators using the `Indicators` class (sequential vs parallel).
- [x] Task: Implement a "Synchronization Check" to ensure indicators from different timeframes are based on consistent price levels.
- [x] Task: Document rate-limiting constraints when fetching 4+ timeframes for the entire Top 50.
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: MTF Alignment Logic & Trend Scoring [checkpoint: 9155a18]
Goal: Develop a scoring system based on indicator alignment across timeframes.

- [x] Task: Define "MTF Alignment" rules (e.g., RSI > 50 on all timeframes, or Price > EMA200 on 4h and 1d).
- [x] Task: Create a prototype scoring engine that ranks candidates by "Trend Quality Score".
- [x] Task: Research the impact of "Fractal Resistance" (e.g., short-term trend up but long-term trend down).
- [x] Task: Conductor - User Manual Verification 'Phase 3'

## Phase 4: Prototyping & Final Research Report [checkpoint: 9155a18]
Goal: Deliver a proof-of-concept tool and feasibility report.

- [x] Task: Create `scripts/filter_mtf_candidates.py` to generate a high-conviction shortlist.
- [x] Task: Final Report: Performance analysis of MTF filtering vs. single-timeframe scanning.
- [x] Task: Conductor - User Manual Verification 'Phase 4'