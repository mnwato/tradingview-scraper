# Plan: Explore and Review Top50 Crypto CEX Base Universes

This plan outlines the steps to audit, optimize, and verify the top 50 base universe filters for major Crypto CEXs.

## Phase 1: Audit & Baseline Analysis
- [x] Task: Document current filtering criteria in `configs/crypto_cex_base_top50_*.yaml`
- [x] Task: Run baseline scans with current configs and capture output metrics (liquidity, market cap)
- [x] Task: Identify discrepancies between "Top 50" intent and actual scanner results
- [x] Task: Conductor - User Manual Verification 'Audit & Baseline Analysis' (Protocol in workflow.md)

## Phase 2: Filter Optimization (TDD Approach)
- [x] Task: TDD - Create a verification script `scripts/verify_universe_quality.py` to test JSON output against "tradability" thresholds
- [x] Task: Optimize filters for Binance (Spot & Perps) in YAML configs
- [x] Task: Optimize filters for OKX (Spot & Perps) in YAML configs
- [x] Task: Optimize filters for Bybit (Spot & Perps) in YAML configs
- [x] Task: Optimize filters for Bitget (Spot & Perps) in YAML configs
- [x] Task: Conductor - User Manual Verification 'Filter Optimization' (Protocol in workflow.md)

## Phase 3: Verification & Final Reporting
- [x] Task: Rerun all crypto scans and summarizers with optimized configs
- [x] Task: Validate improved quality using the `verify_universe_quality.py` script
- [x] Task: Generate a summary report comparing baseline vs. optimized universes
- [x] Task: Conductor - User Manual Verification 'Verification & Final Reporting' (Protocol in workflow.md)
