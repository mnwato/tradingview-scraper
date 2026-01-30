---
name: quant-discover
description: Discover candidate assets from exchanges and data sources. Use when the user wants to scan for new assets, update the candidate universe, or explore available symbols on Binance, TradingView, or other sources.
compatibility: Claude Code
metadata:
  author: quant-team
  version: "1.0"
  pipeline: discovery
allowed-tools: Bash(python:*) Bash(make:*) Read
---

# Quant Discovery Pipeline

Scan exchanges and data sources to discover candidate assets for the selection pipeline.

## When to use this skill

Use this skill when the user wants to:
- Scan for new assets on Binance
- Update the candidate universe
- Explore available symbols
- Run discovery scanners

## Available scanners

- `binance_spot` - Binance spot pairs (USDT quoted)
- `binance_perp` - Binance perpetual futures
- `tradingview` - TradingView screener results
- `okx_spot` - OKX spot pairs

## How to run

1. **Run a specific scanner**:
   ```bash
   make scan-run SCANNER=binance_spot
   ```

2. **Run all configured scanners**:
   ```bash
   make scan-run
   ```

3. **Check discovered candidates**:
   ```bash
   cat data/export/latest/candidates.json | jq '. | length'
   ```

## Example usage

User: "Discover Binance spot assets"
→ Execute: `make scan-run SCANNER=binance_spot`

## Output

Report:
1. Number of candidates discovered
2. Exchanges/sources scanned
3. Path to candidates file
