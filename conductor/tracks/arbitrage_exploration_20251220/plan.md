# Implementation Plan: Arbitrage and Multi-Quote Pair Exploration

## Phase 1: Research & Data Extraction [checkpoint: f5908f2]
Goal: Identify and extract high-liquidity pairs with multiple quotes from existing universe results.

- [x] Task: Audit Binance Spot and Perp base universes for symbols with `alternates`.
- [x] Task: Apply trend strategy filters (Long/Short) to narrow down the candidate list.
- [x] Task: Export a clean mapping of `Primary Symbol -> List of Alternates` for targeted scanning.
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Arbitrage Scanning Tooling [checkpoint: f5908f2]
Goal: Develop a diagnostic tool to scan for real-time price discrepancies across quotes.

- [x] Task: Create `scripts/scan_arbitrage.py` to fetch real-time prices for primary and alternate symbols.
- [x] Task: Implement spread calculation (Bid/Ask aware) and percentage discrepancy reporting.
- [x] Task: Support both Spot-Spot and Perp-Perp multi-quote comparisons.
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Execution & Opportunity Analysis [checkpoint: f5908f2]
Goal: Run the scanner and analyze findings for tradeable arbitrage opportunities.

- [x] Task: Execute the arbitrage scanner on the trend-filtered candidate list.
- [x] Task: Analyze liquidity/volume depth for both primary and alternate pairs to ensure tradeability.
- [x] Task: Document top candidate pairs for institutional execution.
- [x] Task: Conductor - User Manual Verification 'Phase 3'