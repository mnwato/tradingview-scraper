---
name: quant-select
description: Run the quantitative asset selection pipeline. Use when the user wants to select assets for a portfolio, run HTR filtering, or identify winners from a universe of candidates. Supports crypto, equities, and multi-asset profiles.
compatibility: Claude Code
metadata:
  author: quant-team
  version: "1.0"
  pipeline: selection
allowed-tools: Bash(python:*) Bash(make:*) Read
---

# Quant Selection Pipeline

Run the HTR v3.4 (Hierarchical Threshold Relaxation) selection pipeline to identify high-quality assets for portfolio construction.

## When to use this skill

Use this skill when the user wants to:
- Select assets for a new portfolio
- Run the selection pipeline for a specific profile
- Identify winners from a candidate universe
- Test different selection parameters

## Arguments

The skill accepts a profile name as the primary argument:

- `crypto_long` - Binance spot assets, long-only
- `crypto_short` - Binance spot assets, short-only  
- `binance_spot_rating_ma_long` - MA-based trend following
- `meta_benchmark` - Multi-sleeve meta-portfolio

## How to run

1. **Check available profiles**:
   ```bash
   cat configs/manifest.json | jq '.profiles | keys'
   ```

2. **Run the selection pipeline**:
   ```bash
   python scripts/run_production_pipeline.py --profile $ARGUMENTS
   ```

3. **Check the results**:
   - Winners: `data/artifacts/summaries/latest/portfolio_winners.json`
   - Audit trail: `data/artifacts/summaries/latest/audit.jsonl`

## Example usage

User: "Run selection for crypto long"
→ Execute: `python scripts/run_production_pipeline.py --profile crypto_long`

## Output

After successful execution, report:
1. Number of winners selected
2. Relaxation stage reached (1-4)
3. Path to the winners file
4. Any warnings from the audit trail
