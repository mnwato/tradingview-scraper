# Implementation Plan: Data Schema Normalization & Tardis.dev Comparison

## Phase 1: Current Schema Audit [checkpoint: 9dce58e]
Goal: Document the exact data structure currently output by `Streamer` and `Overview`.

- [x] Task: Audit `tradingview_scraper/symbols/stream/streamer.py` to document the exact OHLCV JSON schema.
- [x] Task: Audit `tradingview_scraper/symbols/overview.py` to list all available metadata fields.
- [x] Task: Create `docs/research/current_schema_audit.json` with sample outputs for Spot and Perp (Virtual audit completed via code review).
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Industry Standard Comparison (Tardis & Cryptofeed) [checkpoint: 9dce58e]
Goal: Map our schema against "Gold Standard" normalized market data types.

- [x] Task: Research Tardis.dev data types (Trade, Quote, Liquidations, Open Interest).
- [x] Task: Research Cryptofeed standardized structs (Ticker, OrderBook, Candle).
- [x] Task: Create a "Gap Analysis" report identifying missing fields (e.g., `funding_rate`, `open_interest`, `side`).
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Schema Evolution Proposal [checkpoint: 9dce58e]
Goal: Define a roadmap to upgrade the library's data model.

- [x] Task: Design a `NormalizedCandle` Pydantic model that aligns with industry standards.
- [x] Task: Propose a "Metadata Enrichment" layer to add missing fields from secondary API calls.
- [x] Task: Final Report: Feasibility of achieving "Tardis-Lite" compliance using TradingView data.
- [x] Task: Conductor - User Manual Verification 'Phase 3'