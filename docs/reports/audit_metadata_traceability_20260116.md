# Audit Report: Metadata Traceability (2026-01-16)

## 1. Executive Summary
**Status**: ✅ **VERIFIED**
The current architecture supports the requirement to "keep BTC.P as an alternative to BTC" through the existing `implementation_alternatives` field. The "Canonical Consolidation" logic in `scripts/select_top_universe.py` already captures redundant venues and attaches them to the primary candidate. This metadata is propagated through the entire pipeline (Selection -> Optimization -> Audit Ledger), ensuring downstream Execution Routers can hydrate orders with the correct instrument (Spot or Perp).

## 2. Evidence of Compliance

### 2.1 Discovery & Deduplication (`select_top_universe.py`)
- **Logic**: Lines 226-229 explicitly capture alternatives:
  ```python
  # Track alternatives (other venues for the SAME logic/direction)
  primary["implementation_alternatives"] = [
      {"symbol": x["symbol"], ...} for x in group[1:]
  ]
  ```
- **Outcome**: If `BTCUSDT` (Spot) is selected as primary, `BTCUSDT.P` (Perp) is saved in `implementation_alternatives` if it was present in the scan.

### 2.2 Pipeline Propagation (`backtest_engine.py`)
- **Loading**: `load_data()` loads the full candidate object into `self.metadata`.
- **Selection**: The Selection Engine passes the full metadata object (including alternatives) to the `winners` list.
- **Persistence**: The `backtest_select` event in `audit.jsonl` records the full `winners_meta`, preserving the alternatives for posterity.

### 2.3 Gap Analysis: Current Profiles
- **Gap**: The current `binance_spot_rating_*` profiles explicitly filter for `type: spot` in the scanner config.
- **Implication**: `BTC.P` is never discovered, so it cannot be added as an alternative.
- **Remediation**: To fully enable this feature, we must update the scanner configs (`configs/scanners/crypto/ratings/*.yaml`) to allow `type: swap` (Perps) but rely on the deduplication logic to prioritize Spot as the *primary* analysis asset.

## 3. Recommendation
No code changes are required in the python scripts. The logic exists and is correct.
To activate this feature operationally, we would simply need to broaden the scanner filters in a future update to include Perps, trusting `select_top_universe.py` to fold them into the Spot identity.

**Verdict**: The system design is **Forward-Compatible** with the requirement.
