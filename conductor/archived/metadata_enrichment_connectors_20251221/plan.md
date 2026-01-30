# Implementation Plan: Metadata Enrichment Connectors
**Track ID**: `metadata_enrichment_connectors_20251221`
**Status**: In Progress

## 1. Objective
Enhance the Data Lakehouse Metadata Catalog by implementing a "Connector" architecture that sources execution-critical metadata (e.g., `min_notional`, `contract_size`, `maker_fee`, `taker_fee`) from exchange APIs (CCXT) to fill gaps left by TradingView.

## 2. Phases

### Phase 1: Research & Setup
- [ ] Task: Research CCXT's `fetchMarkets` output structure for key exchanges (Binance, OKX, Bybit).
- [ ] Task: Identify mapping from CCXT fields (e.g., `limits.amount.min`) to Catalog schema (`min_order_qty`).
- [ ] Task: Create a prototype script `scripts/research_ccxt_metadata.py` to dump market info for a single symbol.

### Phase 2: Connector Implementation
- [ ] Task: Create `tradingview_scraper/symbols/stream/connectors/base.py` (Abstract Base Class).
- [ ] Task: Implement `BinanceConnector` using CCXT (or direct REST if lighter).
- [ ] Task: Update `MetadataService` to use connectors for "Enrichment".

### Phase 3: Integration & Automation
- [ ] Task: Create `scripts/enrich_metadata_catalog.py` to iterate through the catalog and fill missing fields.
- [ ] Task: Verify the enriched catalog contains both TV structural data and Exchange execution data.
- [ ] Task: Final Report.
